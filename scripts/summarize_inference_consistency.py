"""Aggregate and independently verify the completed diagnostic artifacts."""

import argparse
import json
import subprocess
from pathlib import Path
import statistics
import torch
import numpy as np

from lost_tokens.core import atomic_json, digest, file_digest, now

torch.set_num_threads(2)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("work_dir", type=Path)
parser.add_argument("--source-method-commit", required=True)
parser.add_argument("--code-branch")
args = parser.parse_args()
root = args.work_dir
manifest = json.loads((root / "manifest.json").read_text())
rows = []
evidence = {}
source_experiments = set()
for task, entry in manifest["tasks"].items():
    inp = json.loads((root / f"inputs/{task}.json").read_text())
    assert file_digest(root / f"inputs/{task}.json") == entry["input_sha256"]
    found = list((root / "workers").glob(f"*/{task}/*.json"))
    assert len(found) == entry["prefixes"], (task, len(found), entry["prefixes"])
    assert {json.loads(f.read_text())["id"] for f in found} == set(entry["ids"])
    for source in entry["cases"]:
        case = Path(source["case_path"])
        assert file_digest(case) == source["case_sha256"]
        assert file_digest(case.parents[3] / "identity.json") == source["worker_identity_sha256"]
        source_cfg = json.loads((case.parents[3] / "resolved-config.json").read_text())
        # The task config lists available arms; the evaluated worker records
        # only filtered_futures. Diagnostic forward requests run no AR arm.
        assert source_cfg["experiment"]["arms"] == ["filtered_futures"]
        assert {k: v for k, v in source_cfg["experiment"].items() if k != "arms"} == {
            k: v for k, v in inp["config"]["experiment"].items() if k != "arms"
        }
        assert source_cfg["model"] == inp["config"]["model"]
        source_experiments.add(digest(source_cfg["experiment"]))
    by_key = {(p["id"], p["kind"]): p for p in inp["probes"]}
    for f in found:
        d = json.loads(f.read_text())
        p = by_key[d["id"], d["kind"]]
        assert d["prefix_sha256"] == digest(p["ids"])
        assert all(v["prefix_sha256"] == d["prefix_sha256"] for v in d["observations"].values())
        assert d["observations"]["fresh1"]["cached_tokens"] == 0
        assert d["observations"]["fresh2"]["cached_tokens"] == 0
        assert d["observations"]["batch1"]["cached_tokens"] == 0
        assert d["observations"]["batch2"]["cached_tokens"] == 0
        assert d["observations"]["warm"]["cached_tokens"] > 0
        vectors = np.load(f.with_suffix(".npz"))
        assert set(vectors.files) == set(d["observations"])
        assert all(np.isfinite(vectors[k]).all() for k in vectors.files)
        pairs = {
            "fresh_repeat": ("fresh1", "fresh2"),
            "warm_vs_fresh": ("fresh1", "warm"),
            "incremental_vs_fresh": ("fresh1", "incremental64"),
            "batch_vs_fresh": ("fresh1", "batch1"),
            "batch_repeat": ("batch1", "batch2"),
            "parent_cache": ("parent_before_rollouts", "parent_after_rollouts"),
        }
        if d["kind"] == "compaction":
            pairs["compaction_rebuild"] = ("fresh1", "compaction_warm_rebuild")
        for label, (a, b) in pairs.items():
            x, y = torch.from_numpy(vectors[a]), torch.from_numpy(vectors[b])
            lx, ly = x.log_softmax(-1), y.log_softmax(-1)
            px, py = lx.exp(), ly.exp()
            c = d["comparisons"][label]
            assert c["identical"] == torch.equal(x, y)
            for key, value in (
                ("max_abs_logit", float((x - y).abs().max())),
                ("max_abs_logprob", float((lx - ly).abs().max())),
                ("mean_abs_logprob", float((lx - ly).abs().mean())),
                ("max_abs_probability", float((px - py).abs().max())),
                ("total_variation", float((px - py).abs().sum() / 2)),
            ):
                assert abs(c[key] - value) < 1e-6, (key, c[key], value)
            oa, ob = d["observations"][a], d["observations"][b]
            assert c["top1_changed"] == (
                oa["distribution"]["top_token_id"] != ob["distribution"]["top_token_id"]
            )
            assert c["top2_order_changed"] == (
                [r["id"] for r in oa["top20"][:2]] != [r["id"] for r in ob["top20"][:2]]
            )
            assert c["fork_gate_changed"] == (
                oa["distribution"]["eligible"] != ob["distribution"]["eligible"]
            )
        if d["branch_scores"]:
            from lost_tokens.recurrent_memory import select_rollout, memory_quality_gate
            from transformers import GenerationConfig

            cfg = inp["config"]["model"]
            generation = GenerationConfig.from_pretrained(
                cfg["name"],
                revision=cfg["revision"],
                cache_dir=cfg["cache_dir"],
                local_files_only=True,
            )
            eos_ids = set(
                generation.eos_token_id
                if isinstance(generation.eos_token_id, list)
                else [generation.eos_token_id]
            )
            for label, v in d["branch_scores"]["variants"].items():
                previews = [
                    {**old, "raw_log_probabilities": lp}
                    for old, lp in zip(p["event"]["previews"], v["raw_log_probabilities"])
                ]
                selection = select_rollout(previews, inp["config"]["experiment"], eos_ids)
                assert v["selection"] == selection
                assert v["memory_quality"] == memory_quality_gate(
                    previews, selection, inp["config"]["experiment"]
                )
        rows.append(d)
        evidence[str(f.relative_to(root))] = {
            "json_sha256": file_digest(f),
            "vectors_sha256": file_digest(f.with_suffix(".npz")),
        }

assert len(rows) == sum(t["prefixes"] for t in manifest["tasks"].values())
workers = []
for env in (root / "workers").glob("*/environment.json"):
    e = json.loads(env.read_text())
    assert e["source_commit"] == manifest["code_commit"]
    complete = json.loads((env.parent / "completion.json").read_text())
    workers.append({"worker": env.parent.name, "environment": e, "completion": complete})
worker_tasks = [task for w in workers for task in w["environment"]["tasks"]]
assert len(worker_tasks) == len(set(worker_tasks))
assert set(worker_tasks) == set(manifest["tasks"])


def aggregate(subset):
    result = {
        "questions": len({(r["task"], r["id"]) for r in subset}),
        "prefixes": len(subset),
        "comparisons": {},
    }
    labels = sorted(set(k for r in subset for k in r["comparisons"]))
    for label in labels:
        # A compaction prefix has no candidate event: its parent-cache query is
        # just a repeated warm forward, not a real candidate-isolation test.
        selected = [
            r
            for r in subset
            if label in r["comparisons"]
            and not (label == "parent_cache" and r["kind"] == "compaction")
        ]
        vals = [r["comparisons"][label] for r in selected]
        result["comparisons"][label] = {
            "prefixes": len(vals),
            "nonidentical": sum(not c["identical"] for c in vals),
            **{
                key: sum(c[key] for c in vals)
                for key in ("top1_changed", "top2_order_changed", "fork_gate_changed")
            },
            "max_abs_probability": max((c["max_abs_probability"] for c in vals), default=0),
            "median_max_abs_probability": statistics.median(c["max_abs_probability"] for c in vals)
            if vals
            else 0,
            "max_abs_logit": max((c["max_abs_logit"] for c in vals), default=0),
            "max_abs_logprob": max((c["max_abs_logprob"] for c in vals), default=0),
            "affected_questions": len(
                {
                    r["id"]
                    for r in selected
                    if r["comparisons"][label]["top1_changed"]
                    or r["comparisons"][label]["fork_gate_changed"]
                }
            ),
        }
    branches = [r["branch_scores"] for r in subset if r["branch_scores"]]
    result["teacher_forced_branches"] = {
        "questions": len(branches),
        "selection_changed": sum(b["selected_rank_changed"] for b in branches),
        "memory_gate_changed": sum(b["memory_gate_changed"] for b in branches),
    }
    return result


summary = {
    "created": now(),
    "scope": f"{len({(r['task'], r['id']) for r in rows})}-question diagnostic; no new accuracy measurement or AR baseline run",
    "code_commit": manifest["code_commit"],
    "code_branch": args.code_branch
    or subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
    "source_method_commit": args.source_method_commit,
    "overall": aggregate(rows),
    "datasets": {t: aggregate([r for r in rows if r["task"] == t]) for t in manifest["tasks"]},
    "workers": workers,
    "examples": {},
    "metric_notes": {
        "top1_changed": "production decoder topk(6) top token, using CUDA tie-breaking",
        "top2_order_changed": "ordering of first two entries of diagnostic CUDA topk(20); ties can differ from production topk(6); not used for production-rank conclusions",
        "fork_gate_changed": "production decoder eligibility: top token non-special and two non-special probabilities >=0.2",
        "teacher_forced_branches": "fixed saved continuation pairs; excludes forced first token; does not measure free-running choice or answer accuracy",
        "incremental_vs_fresh": "up to last 64 generated context tokens decoded incrementally, earlier prefix freshly prefilled; not full token-by-token replay of entire context",
    },
}
for label in ("warm_vs_fresh", "incremental_vs_fresh", "batch_vs_fresh"):
    changed = [
        r
        for r in rows
        if r["comparisons"][label]["top1_changed"] or r["comparisons"][label]["fork_gate_changed"]
    ]
    summary["examples"][label] = [
        {
            "id": r["id"],
            "task": r["task"],
            "kind": r["kind"],
            "prefix_length": r["prefix_length"],
            "prefix_sha256": r["prefix_sha256"],
            "comparison": r["comparisons"][label],
            "reference": r["observations"]["fresh1"]["distribution"],
            "variant": r["observations"][
                {
                    "warm_vs_fresh": "warm",
                    "incremental_vs_fresh": "incremental64",
                    "batch_vs_fresh": "batch1",
                }[label]
            ]["distribution"],
        }
        for r in changed[:5]
    ]
atomic_json(root / "summary.json", summary)
atomic_json(
    root / "diagnostic-audit.json",
    {
        "passed": True,
        "created": now(),
        "questions": len({(r["task"], r["id"]) for r in rows}),
        "prefixes": len(rows),
        "audit_tool_sha256": file_digest(Path(__file__)),
        "audit_code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "manifest_sha256": file_digest(root / "manifest.json"),
        "summary_sha256": file_digest(root / "summary.json"),
        "checks": [
            "exact selected question coverage",
            "input manifest/source case/worker identity hashes",
            "source experiment/model configs match",
            "all reconstructed prefix hashes match every mode",
            "fresh/batch cache miss and warm cache hit verified",
            "all saved logits finite",
            "full-vocabulary differences independently recomputed",
            "branch selection and memory gates recomputed from teacher-forced statistics",
            "all workers completed on frozen code with exact task coverage",
        ],
        "evidence": evidence,
    },
)
print(json.dumps({"overall": summary["overall"], "datasets": summary["datasets"]}, indent=2))
