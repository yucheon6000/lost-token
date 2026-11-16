"""Read-only vLLM consistency diagnostic on fixed samples of saved Ours runs.

This is not a benchmark arm, does not generate accuracy scores, and never writes
to its source runs or the canonical cohort. See --help for reproducible commands.
"""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from lost_tokens.core import atomic_json, digest, file_digest, now
from lost_tokens.recurrent_memory import compact_history, instruction


TASKS = ("aime25", "hmmt25", "gsm8k", "gpqa", "math500", "mmlu")
SAMPLE_RULE = "lost-tokens/consistency-v1/{task}/{id}"


def engine_tokens_match(actual, expected, eos_ids):
    if expected and expected[-1] in eos_ids and actual == expected[:-1]:
        return True
    return actual[: len(expected)] == expected and actual[len(expected) :] in ([], [min(eos_ids)])


def incremental_tail_length(probe):
    # Prompt chat boundaries can be EOS IDs. Keep those in the prefill and only
    # replay generated body tokens, stopping at the recorded pre-fork context.
    return min(64, len(probe["body_ids"]), len(probe["ids"]) - 1)


def sample_ids(ids, task, count):
    if count > len(ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid sample/cohort size")
    return sorted(
        ids,
        key=lambda ident: hashlib.sha256(
            SAMPLE_RULE.format(task=task, id=ident).encode()
        ).hexdigest(),
    )[:count]


def reconstruct(case, base, exp):
    """Replay exact token ledgers and assert every saved event/final hash.

    Compaction precedes a fork at the same body position. Capture both the first
    and middle fork plus the first compacted prefix, without selecting by score.
    """
    result = case["conditions"]["filtered_futures"]
    events, body = result["events"], result["body_ids"]
    context, history, consumed = list(base), [], 0
    compactions = iter(result["compactions"])
    compact = next(compactions, None)
    selected = {0, len(events) // 2} if events else set()
    probes = []

    def advance(position):
        nonlocal consumed
        assert position >= consumed
        part = body[consumed:position]
        context.extend(part)
        history.append({"kind": "body", "ids": part})
        consumed = position

    def rebuild(record):
        nonlocal context, history
        before = list(context)
        history, removed = compact_history(history, exp["memory_compact_to_tokens"])
        assert removed == record["removed_events"]
        context = list(base) + [token for block in history for token in block["ids"]]
        assert len(context) == record["remaining_context_length"]
        assert [token for h in history if h["kind"] == "body" for token in h["ids"]] == body[
            :consumed
        ]
        if not any(p["kind"] == "compaction" for p in probes):
            probes.append(
                {
                    "kind": "compaction",
                    "ids": list(context),
                    "body_ids": body[:consumed],
                    "event": None,
                    "before_compaction_ids": before,
                }
            )

    for index, event in enumerate(events):
        while compact is not None and compact["body_position"] <= event["body_position"]:
            advance(compact["body_position"])
            rebuild(compact)
            compact = next(compactions, None)
        advance(event["body_position"])
        assert digest(context) == event["root_sha256"]
        assert len(context) == event["root_length"]
        if index in selected:
            probes.append(
                {
                    "kind": "first" if index == 0 else "middle",
                    "ids": list(context),
                    "body_ids": body[:consumed],
                    "event": event,
                }
            )
        if event["memory_ids"]:
            context.extend(event["memory_ids"])
            history.append({"kind": "memory", "ids": event["memory_ids"], "event": index})
        assert digest(context) == event["continuation_root_sha256"]
        committed = event["committed_ids"]
        assert committed == body[consumed : consumed + len(committed)]
        context.extend(committed)
        history.append({"kind": "body", "ids": committed})
        consumed += len(committed)
        assert digest(context) == event["after_commit_sha256"]
    while compact is not None:
        advance(compact["body_position"])
        rebuild(compact)
        compact = next(compactions, None)
    advance(len(body))
    assert digest(context) == result["final_context_sha256"]
    if not probes:
        probes.append({"kind": "no-fork", "ids": list(base), "body_ids": [], "event": None})
    return probes


def prepare(args):
    from transformers import AutoTokenizer

    spec = json.loads(args.config.read_text())
    cfg = spec["model"]
    tok = AutoTokenizer.from_pretrained(
        cfg["name"], revision=cfg["revision"], cache_dir=cfg["cache_dir"], local_files_only=True
    )
    manifest = {
        "schema": 1,
        "created": now(),
        "scope": "diagnostic, not accuracy evaluation",
        "sampling_rule": SAMPLE_RULE,
        "count_per_task": args.count,
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "tasks": {},
    }
    for task in TASKS:
        cohort = args.shared_root / "evaluation/subsets/l40s-2h-v1" / f"{task}.json"
        ids = sample_ids(json.loads(cohort.read_text())["ids"], task, args.count)
        run = args.source_root / f"{args.run_prefix}-{task}"
        probes, cases = [], []
        for ident in ids:
            matches = list((run / "workers").glob(f"*/cases/*/*/{ident}.json"))
            assert len(matches) == 1
            path = matches[0]
            case = json.loads(path.read_text())
            worker = path.parents[3]
            audit = json.loads((worker / "audit.json").read_text())
            assert not audit["partial"]
            assert audit["case_sha256"][str(path.relative_to(worker))] == file_digest(path)
            base = tok.apply_chat_template(
                [{"role": "user", "content": instruction(case) + case["question"]}],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=True,
            )
            assert len(base) == case["prompt_tokens"]
            case_probes = reconstruct(case, base, spec["experiment"])
            for p in case_probes:
                p.update(task=task, id=ident, root_sha256=digest(p["ids"]))
            probes.extend(case_probes)
            cases.append(
                {
                    "id": ident,
                    "case_sha256": file_digest(path),
                    "case_path": str(path.resolve()),
                    "worker_identity_sha256": file_digest(worker / "identity.json"),
                    "probe_kinds": [p["kind"] for p in case_probes],
                }
            )
        task_config = copy.deepcopy(spec)
        task_config["model"]["vllm_batch_size"] = 4 if task in ("aime25", "hmmt25") else 8
        atomic_json(
            args.work_dir / f"inputs/{task}.json", {"config": task_config, "probes": probes}
        )
        manifest["tasks"][task] = {
            "ids": ids,
            "cohort_sha256": file_digest(cohort),
            "cases": cases,
            "input_sha256": file_digest(args.work_dir / f"inputs/{task}.json"),
            "prefixes": len(probes),
        }
    atomic_json(args.work_dir / "manifest.json", manifest)
    print(
        json.dumps(
            {
                t: {"questions": len(v["ids"]), "prefixes": v["prefixes"]}
                for t, v in manifest["tasks"].items()
            }
        ),
        flush=True,
    )


def worker(args):
    import numpy as np
    import torch
    from vllm import SamplingParams
    from lost_tokens.vllm_backend import ProtocolProcessor, VLLMModel
    from lost_tokens.recurrent_memory import (
        StreamState,
        StreamDecoder,
        select_rollout,
        memory_quality_gate,
    )

    # VLLMModel sets the pinned V0 environment before constructing the engine.
    # Set it before importing vllm as well, since vllm caches some environment reads.
    inputs = {
        task: json.loads((args.work_dir / f"inputs/{task}.json").read_text()) for task in args.tasks
    }
    manifest = json.loads((args.work_dir / "manifest.json").read_text())
    for task in args.tasks:
        assert (
            file_digest(args.work_dir / f"inputs/{task}.json")
            == manifest["tasks"][task]["input_sha256"]
        )
    cfg = copy.deepcopy(inputs[args.tasks[0]]["config"]["model"])
    assert all(
        v["config"]["model"]["vllm_batch_size"] == cfg["vllm_batch_size"] for v in inputs.values()
    )
    model = VLLMModel(cfg)
    llm = model.engine.llm
    outdir = args.work_dir / "workers" / args.worker_name
    outdir.mkdir(parents=True, exist_ok=True)
    atomic_json(
        outdir / "environment.json",
        {
            "created": now(),
            "config": cfg,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(),
            "tasks": args.tasks,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "pip": subprocess.check_output(["uv", "pip", "freeze"], text=True),
        },
    )
    started = time.monotonic()

    class Probe(ProtocolProcessor):
        def __init__(self, p, exp, forced=(), root_ids=None):
            root = StreamState(
                list(p["ids"] if root_ids is None else root_ids), None, None, list(p["body_ids"])
            )
            super().__init__(model, exp, root, len(forced) + 1, 0)
            self.forced, self.vector, self.actual_prefix_sha256 = list(forced), None, None

        def __call__(self, output_ids, logits):
            assert list(output_ids) == self.ids
            offset = len(self.ids)
            if offset > len(self.forced):
                raise RuntimeError("Probe exceeded forced path")
            values = logits.float()
            if offset == len(self.forced):
                self.vector = values.detach().cpu().numpy().copy()
                self.actual_prefix_sha256 = digest(self.root.ids + self.ids)
                token = min(model.eos_ids)
            else:
                token = self.forced[offset]
                self.logprobs.append(float(values.log_softmax(-1)[token]))
            self.ids.append(token)
            logits.fill_(-torch.inf)
            logits[token] = 0
            return logits

    def run(processors, reset=False):
        if reset:
            assert llm.reset_prefix_cache(), "Prefix cache reset failed"
        model.engine.processors = {id(p): p for p in processors}
        params = [
            SamplingParams(
                temperature=0,
                max_tokens=p.count + 1,
                stop_token_ids=sorted(model.eos_ids),
                extra_args={"lost_tokens_processor": id(p)},
                detokenize=False,
                seed=0,
            )
            for p in processors
        ]
        outputs = llm.generate(
            [{"prompt_token_ids": p.root.ids} for p in processors], params, use_tqdm=False
        )
        assert len(outputs) == len(processors)
        for p, output in zip(processors, outputs):
            actual, expected = list(output.outputs[0].token_ids), p.ids
            assert engine_tokens_match(actual, expected, model.eos_ids)
            p.cached_tokens = output.num_cached_tokens
            if isinstance(p, Probe):
                assert len(p.logprobs) == len(p.forced)
                if not p.forced or p.forced[-1] not in model.eos_ids:
                    assert p.actual_prefix_sha256 == digest(p.root.ids + p.forced)
        model.engine.processors = {}
        return processors

    def observed(p, exp):
        # Match the production CUDA topk tie-breaking and log-softmax path.
        vector = torch.from_numpy(p.vector).to(model.device)
        lp = vector.log_softmax(-1)
        vals, ids = lp.topk(20)
        dec = StreamDecoder(model, exp)
        dist = dec.candidates(StreamState([], None, vector))
        return {
            "prefix_sha256": p.actual_prefix_sha256,
            "cached_tokens": p.cached_tokens,
            "distribution": dist,
            "top20": [{"id": int(i), "p": float(v.exp())} for i, v in zip(ids, vals)],
        }

    def compare(a, b, exp):
        x, y = torch.from_numpy(a.vector), torch.from_numpy(b.vector)
        lx, ly = x.log_softmax(-1), y.log_softmax(-1)
        px, py = lx.exp(), ly.exp()
        ax, by = observed(a, exp), observed(b, exp)
        return {
            "identical": bool(torch.equal(x, y)),
            "max_abs_logit": float((x - y).abs().max()),
            "max_abs_logprob": float((lx - ly).abs().max()),
            "mean_abs_logprob": float((lx - ly).abs().mean()),
            "max_abs_probability": float((px - py).abs().max()),
            "total_variation": float((px - py).abs().sum() / 2),
            "top1_changed": ax["distribution"]["top_token_id"]
            != by["distribution"]["top_token_id"],
            "top2_order_changed": [v["id"] for v in ax["top20"][:2]]
            != [v["id"] for v in by["top20"][:2]],
            "fork_gate_changed": ax["distribution"]["eligible"] != by["distribution"]["eligible"],
        }

    for task, inp in inputs.items():
        exp, probes = inp["config"]["experiment"], inp["probes"]
        batch_size = cfg["vllm_batch_size"]
        # Fill batch with distinct questions, not duplicate copies of the target.
        peers = [p for p in probes if p["kind"] in ("middle", "no-fork")]
        if len(peers) < batch_size:
            peers = [p for p in probes if p["kind"] == "first"]
        for index, p in enumerate(probes):
            dest = outdir / task / f"{p['id']}-{p['kind']}.json"
            if dest.exists():
                raise RuntimeError(f"Refusing to overwrite diagnostic: {dest}")
            other = [v for v in peers if v["id"] != p["id"]][: batch_size - 1]
            assert len(other) == batch_size - 1
            modes = {}
            modes["fresh1"] = run([Probe(p, exp)], reset=True)[0]
            modes["fresh2"] = run([Probe(p, exp)], reset=True)[0]
            modes["warm"] = run([Probe(p, exp)])[0]
            tail = incremental_tail_length(p)
            assert tail > 0, "Need at least one generated token for incremental test"
            modes["incremental64"] = run(
                [Probe(p, exp, p["ids"][-tail:], p["ids"][:-tail])], reset=True
            )[0]
            modes["batch1"] = run([Probe(p, exp)] + [Probe(v, exp) for v in other], reset=True)[0]
            modes["batch2"] = run([Probe(p, exp)] + [Probe(v, exp) for v in other], reset=True)[0]
            # Establish a warm parent, execute real independently seeded candidate
            # rollouts, then requery that unchanged parent through the real backend.
            parent_before = run([Probe(p, exp)], reset=True)[0]
            parent_before = run([Probe(p, exp)])[0]
            event = p["event"]
            branch = None
            if event:
                root = StreamState(list(p["ids"]), None, None, list(p["body_ids"]))
                parent_ids, parent_body = list(root.ids), list(root.generated_ids)
                for preview in event["previews"]:
                    roll = ProtocolProcessor(
                        model,
                        exp,
                        root,
                        len(preview["ids"]),
                        preview["seed"],
                        first=preview["ids"][0],
                    )
                    run([roll])
                    assert root.ids == parent_ids and root.generated_ids == parent_body
            modes["parent_after_rollouts"] = run([Probe(p, exp)])[0]
            modes["parent_before_rollouts"] = parent_before
            if event and p["kind"] == "middle":
                single = [run([Probe(p, exp, v["ids"])], reset=True)[0] for v in event["previews"]]
                batch = run(
                    [Probe(p, exp, v["ids"]) for v in event["previews"]]
                    + [Probe(v, exp) for v in other[: batch_size - 2]],
                    reset=True,
                )[:2]
                variants = {}
                for label, group in (("singleton", single), ("batch", batch)):
                    previews = [
                        {**v, "raw_log_probabilities": r.logprobs}
                        for v, r in zip(event["previews"], group)
                    ]
                    selection = select_rollout(previews, exp, model.eos_ids)
                    quality = memory_quality_gate(previews, selection, exp)
                    variants[label] = {
                        "selection": selection,
                        "memory_quality": quality,
                        "raw_log_probabilities": [r.logprobs for r in group],
                    }
                branch = {
                    "scope": "teacher-forced saved continuations, not free-running accuracy",
                    "variants": variants,
                    "selected_rank_changed": variants["singleton"]["selection"]["selected_rank"]
                    != variants["batch"]["selection"]["selected_rank"],
                    "memory_gate_changed": variants["singleton"]["memory_quality"]["retained_ranks"]
                    != variants["batch"]["memory_quality"]["retained_ranks"],
                }
            if p["kind"] == "compaction":
                # The obsolete pre-compaction context is cached before querying
                # the compacted IDs, exactly the cache-rebuild concern being tested.
                run([Probe(p, exp, root_ids=p["before_compaction_ids"])], reset=True)
                modes["compaction_warm_rebuild"] = run([Probe(p, exp)])[0]
            pairs = {
                "fresh_repeat": ("fresh1", "fresh2"),
                "warm_vs_fresh": ("fresh1", "warm"),
                "incremental_vs_fresh": ("fresh1", "incremental64"),
                "batch_vs_fresh": ("fresh1", "batch1"),
                "batch_repeat": ("batch1", "batch2"),
                "parent_cache": ("parent_before_rollouts", "parent_after_rollouts"),
            }
            if p["kind"] == "compaction":
                pairs["compaction_rebuild"] = ("fresh1", "compaction_warm_rebuild")
            assert all(v.actual_prefix_sha256 == p["root_sha256"] for v in modes.values())
            result = {
                "task": task,
                "id": p["id"],
                "kind": p["kind"],
                "prefix_length": len(p["ids"]),
                "body_position": len(p["body_ids"]),
                "incremental_tokens": tail,
                "prefix_sha256": p["root_sha256"],
                "batch_size": batch_size,
                "observations": {k: observed(v, exp) for k, v in modes.items()},
                "comparisons": {k: compare(modes[a], modes[b], exp) for k, (a, b) in pairs.items()},
                "branch_scores": branch,
                "source_distribution": event["distribution"] if event else None,
            }
            atomic_json(dest, result)
            np.savez_compressed(dest.with_suffix(".npz"), **{k: v.vector for k, v in modes.items()})
            atomic_json(
                outdir / "progress.json",
                {
                    "task": task,
                    "done": index + 1,
                    "total": len(probes),
                    "elapsed_seconds": time.monotonic() - started,
                    "updated": now(),
                },
            )
            print(
                f"{task} {index + 1}/{len(probes)} {p['id']} {p['kind']} elapsed={time.monotonic() - started:.1f}s",
                flush=True,
            )
    model.close()
    atomic_json(
        outdir / "completion.json",
        {"completed": now(), "tasks": args.tasks, "elapsed_seconds": time.monotonic() - started},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--shared-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--run-prefix")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--tasks", nargs="+", choices=TASKS)
    parser.add_argument("--worker-name", default="probe")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args)
    else:
        os.environ["VLLM_USE_V1"] = "0"
        worker(args)


if __name__ == "__main__":
    main()
