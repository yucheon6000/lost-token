"""Preregistered full-suite, paired multi-seed evaluation of the main argmax release.

The published historical seed is reused as results, never as inference KV.
New seeds each get an independently audited, frozen AR reference and an ours run.
The generator package is unchanged from main. Completed seed results, not pooled
or voted answers, enter the mean and sample standard deviation.
"""

import argparse
from datetime import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import time
import traceback
from zoneinfo import ZoneInfo

from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.core import atomic_json, atomic_text, digest, file_digest, source_fingerprint
from lost_tokens.data import load_prepared
from lost_tokens.reporting import collect, read_json
from lost_tokens.runner import create_run
from lost_tokens.runtime import environment, install_interrupt_handlers

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location("multiseed_shared", ROOT / "scripts/shared_eval.py")
shared = importlib.util.module_from_spec(loader)
loader.loader.exec_module(shared)
TASKS = ("aime25", "hmmt25", "gpqa", "gsm8k", "math500", "mmlu")


def read(path):
    return json.loads(Path(path).read_text())


def now():
    return datetime.now().astimezone().isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_pipeline(pipeline, cfg):
    if (
        pipeline["protocol"] != "argmax-full-multiseed-v1"
        or pipeline["cohort"] != "full-v1"
        or tuple(pipeline["benchmarks"]) != TASKS
        or pipeline["arms"] != ["baseline", "ours"]
        or pipeline["method"] != "filtered_futures/argmax"
    ):
        raise ValueError("The fixed six-task argmax/full-v1 protocol is required")
    seeds = pipeline["seeds"]
    if (
        len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)
        or pipeline["historical_seed"] not in seeds
        or pipeline["historical_seed"] != cfg["experiment"]["seed"]
    ):
        raise ValueError(
            "Distinct integer seeds including the unchanged historical seed are required"
        )
    if (
        cfg != load_spec(ROOT / "configs/vllm-argmax.json")
        or cfg["experiment"]["selection"] != "argmax"
        or cfg["experiment"]["lookahead"] is not None
        or cfg["model"].get("backend") != "vllm"
    ):
        raise ValueError("Use the exact promoted main argmax preset")


def verify_full_cohort(args, cfg):
    shared.verify_cohort(args.work_dir, cfg, TASKS, args.shared / "evaluation/subsets/shared-v1")
    full = read(args.cohort_manifest)
    if full["version"] != "full-v1":
        raise ValueError("Expected the committed full-v1 cohort")
    source = source_fingerprint()
    for key in ("lost_tokens/data.py", "lost_tokens/datasets.json"):
        if source[key] != full["source"][key]:
            raise ValueError("Frozen dataset source differs")
    cohort = {}
    for task in TASKS:
        entry = full["datasets"][task]
        rows = load_prepared(args.work_dir, cfg, task)
        by_id = {r["id"]: r for r in rows}
        ids = entry["ids"]
        if (
            len(ids) != len(set(ids))
            or len(ids) != entry["n"]
            or entry["n"] != entry["full_n"]
            or len(rows) != len(by_id)
            or set(ids) != set(by_id)
            or digest(ids) != entry["ids_sha256"]
            or digest([by_id[i] for i in ids]) != entry["rows_sha256"]
        ):
            raise ValueError("Full dataset IDs/rows differ: " + task)
        cohort[task] = {"ids": ids, "n": len(ids), "rows_sha256": entry["rows_sha256"]}
    return cohort


def seal_reference(path, payload):
    """A completed baseline is immutable, including its original timing."""
    item = {"payload": payload, "sha256": digest(payload)}
    if path.exists():
        if read(path) != item:
            raise ValueError("Sealed reference changed: " + str(path))
    else:
        atomic_json(path, item)
    return item["sha256"]


def paired_summary(baseline, ours):
    if set(baseline) != set(ours) or not baseline:
        raise ValueError("Paired results must cover exactly the same nonempty ID set")
    n = len(baseline)
    b = sum(r["correct"] for r in baseline.values())
    o = sum(r["correct"] for r in ours.values())
    return {
        "n": n,
        "baseline_correct": b,
        "ours_correct": o,
        "baseline_accuracy": 100 * b / n,
        "ours_accuracy": 100 * o / n,
        "delta_pp": 100 * (o - b) / n,
        "gains": sum(ours[i]["correct"] and not baseline[i]["correct"] for i in baseline),
        "losses": sum(baseline[i]["correct"] and not ours[i]["correct"] for i in baseline),
    }


def aggregate(pairs):
    def stats(key):
        values = [p[key] for p in pairs]
        return {
            "mean": statistics.mean(values) if values else None,
            "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        }

    return {
        "seeds": len(pairs),
        "baseline_accuracy": stats("baseline_accuracy"),
        "ours_accuracy": stats("ours_accuracy"),
        "delta_pp": stats("delta_pp"),
        "positive_seeds": sum(p["delta_pp"] > 0 for p in pairs),
        "tied_seeds": sum(p["delta_pp"] == 0 for p in pairs),
    }


def analyze(state, manifest):
    groups = {}
    for task in TASKS:
        pairs = []
        for seed in manifest["pipeline"]["seeds"]:
            js = [j for j in state["jobs"] if j["task"] == task and j["seed"] == seed]
            if len(js) != 2 or not all(
                j["state"] == "complete" and j.get("audits_passed") for j in js
            ):
                continue
            b = next(j for j in js if j["arm"] == "baseline")
            o = next(j for j in js if j["arm"] == "ours")
            if b["n"] != o["n"] or b["n"] != manifest["cohort"][task]["n"]:
                raise ValueError("Completed seed has incomplete benchmark coverage")
            # Paired gains/losses are computed against sealed ID-level AR results
            # at completion; aggregate only fully audited per-seed scores.
            pairs.append(
                {
                    "seed": seed,
                    "n": b["n"],
                    "baseline_correct": b["correct"],
                    "ours_correct": o["correct"],
                    "baseline_accuracy": 100 * b["correct"] / b["n"],
                    "ours_accuracy": 100 * o["correct"] / o["n"],
                    "delta_pp": 100 * (o["correct"] - b["correct"]) / b["n"],
                    "gains": o["gains"],
                    "losses": o["losses"],
                }
            )
        fresh = [p for p in pairs if p["seed"] != manifest["pipeline"]["historical_seed"]]
        groups[task] = {
            "prospective": aggregate(fresh),
            "all_seeds": aggregate(pairs),
            "pairs": pairs,
        }
    return groups


def historical_results(args, m):
    folder = args.historical_report
    registry = read(folder / "artifact-sha256.json")
    for name, sha in registry.items():
        if file_digest(folder / name) != sha:
            raise ValueError("Historical report artifact changed: " + name)
    p = read(folder / "provenance.json")
    ref = read(folder / "baseline-reference.json")
    if (
        p["release_source_sha256"] != digest(m["source"])
        or p["release_config_sha256"] != file_digest(args.config)
        or p["cohort_manifest_sha256"] != file_digest(args.cohort_manifest)
        or ref["sha256"] != digest(ref["payload"])
        or ref["sha256"] != p["corrected_baseline_reference_sha256"]
        or ref["payload"]["conditions"]["decoding"]["seed"] != m["pipeline"]["historical_seed"]
        or ref["payload"]["conditions"]["runtime"] != m["environment"]["runtime"]
        or read(folder / "environment.json")["gpu_count"] != m["environment"]["gpu_count"]
    ):
        raise ValueError("Historical source/config/cohort/scorer/runtime/allocation differs")
    copied = args.study / "historical-reference"
    copied.mkdir(exist_ok=True)
    inputs = {str(folder / "artifact-sha256.json"): file_digest(folder / "artifact-sha256.json")}
    jobs = []
    seed = m["pipeline"]["historical_seed"]
    metrics = {r["dataset"]: r for r in read(folder / "metrics.json")["rows"]}
    for task in TASKS:
        rows = {}
        for arm, filename in (("baseline", "baseline"), ("ours", "argmax")):
            path = folder / "reports" / task / (filename + "-outcomes.json")
            records = read(path)
            wanted_hash = p["per_task_case_result_sha256"][task][filename]
            if digest(records) != wanted_hash:
                raise ValueError("Historical per-case result hash differs")
            found = {r["id"]: r for r in records}
            if len(found) != len(records) or set(found) != set(m["cohort"][task]["ids"]):
                raise ValueError("Historical full cohort differs")
            if arm == "baseline":
                original = {r["id"]: r for r in ref["payload"]["outcomes"][task]}
                if set(original) != set(found) or any(
                    original[i]["correct"] != r["correct"]
                    or original[i]["prediction"] != r["prediction"]
                    for i, r in found.items()
                ):
                    raise ValueError("Historical baseline differs from sealed reference")
            target = copied / (task + "-" + arm + ".json")
            shutil.copy2(path, target)
            inputs[str(path)] = file_digest(path)
            inputs[str(target)] = file_digest(target)
            rows[arm] = found
            job = {
                "seed": seed,
                "task": task,
                "arm": arm,
                "state": "complete",
                "reused": True,
                "n_required": len(records),
                "n": len(records),
                "correct": sum(r["correct"] for r in records),
                "audits_passed": True,
                "outcomes_file": str(target),
                "outcomes_sha256": digest(records),
                "phase_wall_seconds": metrics[task][
                    "baseline_phase_wall_seconds"
                    if arm == "baseline"
                    else "ours_phase_wall_seconds"
                ],
                "original_generation_code_commit": p["generation_code_commit"],
                "original_full_suite_finished_at": p["historical_full_suite_finished_at"],
            }
            jobs.append(job)
        pair = paired_summary(rows["baseline"], rows["ours"])
        jobs[-1].update(gains=pair["gains"], losses=pair["losses"])
        payload = {
            "seed": seed,
            "task": task,
            "n": pair["n"],
            "correct": pair["baseline_correct"],
            "outcomes": list(rows["baseline"].values()),
            "historical_reference_sha256": ref["sha256"],
            "original_generation_code_commit": p["generation_code_commit"],
            "cohort_manifest_sha256": file_digest(args.cohort_manifest),
            "config": m["config"],
            "timing_scope": "original historical AR measurement",
        }
        path = args.study / "baselines" / str(seed) / (task + ".json")
        sha = seal_reference(path, payload)
        jobs[-2].update(reference_file=str(path), reference_sha256=sha)
        inputs[str(path)] = file_digest(path)
    for name in (
        "baseline-reference.json",
        "provenance.json",
        "config.json",
        "environment.json",
        "metrics.json",
    ):
        inputs[str(folder / name)] = file_digest(folder / name)
    return jobs, inputs


def continue_study(args, m, jobs):
    """Amend seed membership while preserving existing run identities.

    The old scheduler must be stopped before handoff, while its current GPU child
    may finish normally. Completed references/results are retained byte-for-byte;
    an existing unfinished run is resumed at its original path and deadline.
    """
    if args.continuation_study is None:
        return None
    parent_path = args.continuation_study
    parent = read(parent_path / "manifest.json")
    previous = read(parent_path / "status.json")
    if digest(parent) != read(parent_path / "manifest-sha256.json")["sha256"]:
        raise ValueError("Continuation parent manifest changed")
    for key in ("source", "config", "cohort", "gpus", "work_dir", "model_cache"):
        if parent[key] != m[key]:
            raise ValueError("Continuation would change inference/cohort/allocation: " + key)
    if parent["environment"]["runtime"] != m["environment"]["runtime"]:
        raise ValueError("Continuation runtime differs")
    old_seeds, new_seeds = parent["pipeline"]["seeds"], m["pipeline"]["seeds"]
    reduction = bool(getattr(args, "reduce_seeds", False))
    if reduction and not (len(new_seeds) >= 3 and set(new_seeds) < set(old_seeds)):
        raise ValueError("Scope reduction requires a proper subset of at least three seeds")
    if (len(old_seeds) != len(new_seeds) and not reduction) or {
        k: v for k, v in parent["pipeline"].items() if k != "seeds"
    } != {k: v for k, v in m["pipeline"].items() if k != "seeds"}:
        raise ValueError("Continuation changes seeds only; size reduction requires --reduce-seeds")
    removed = set(old_seeds) - set(new_seeds)
    archived_results = []
    for job in previous["jobs"]:
        if job["seed"] not in removed:
            continue
        if reduction and job["state"] == "complete" and job.get("audits_passed"):
            records = read(job["outcomes_file"])
            if digest(records) != job["outcomes_sha256"]:
                raise ValueError("Archived completed outcome identity changed")
            m["inputs"][job["outcomes_file"]] = file_digest(Path(job["outcomes_file"]))
            if job["arm"] == "baseline":
                baseline_for(previous, job["seed"], job["task"])
                m["inputs"][job["reference_file"]] = file_digest(Path(job["reference_file"]))
            archived_results.append(
                {
                    key: job[key]
                    for key in (
                        "seed",
                        "task",
                        "arm",
                        "n",
                        "correct",
                        "outcomes_file",
                        "outcomes_sha256",
                    )
                }
            )
            continue
        if job["state"] != "queued" or job.get("n", 0) or Path(job["run_path"]).exists():
            raise ValueError("Cannot drop an already started seed")
    for name in ("manifest.json", "manifest-sha256.json", "status.json"):
        path = parent_path / name
        m["inputs"][str(path)] = file_digest(path)
    old_jobs = {(j["seed"], j["task"], j["arm"]): j for j in previous["jobs"]}
    inherited = []
    for job in jobs:
        if job["reused"]:
            continue
        old = old_jobs.get((job["seed"], job["task"], job["arm"]))
        if old is None or not Path(old["run_path"]).exists():
            continue
        if load_spec(old["config_file"]) != load_spec(job["config_file"]):
            raise ValueError("Continuation seed configuration differs")
        validate_job_run(old, m, args, complete=old["state"] == "complete")
        new_config, estimate = job["config_file"], job["estimated_seconds"]
        adopted = dict(old)
        adopted.update(
            config_file=new_config,
            estimated_seconds=estimate,
            reused=False,
            state="complete" if old["state"] == "complete" else "queued",
            continued_from={"study": str(parent_path), "manifest_sha256": digest(parent)},
        )
        job.clear()
        job.update(adopted)
        for path in (Path(old["run_path"]) / "plan.json", Path(old["config_file"])):
            m["inputs"][str(path)] = file_digest(path)
        if old["state"] == "complete":
            m["inputs"][old["outcomes_file"]] = file_digest(Path(old["outcomes_file"]))
            if old["arm"] == "baseline":
                baseline_for(previous, old["seed"], old["task"])
                m["inputs"][old["reference_file"]] = file_digest(Path(old["reference_file"]))
        inherited.append(
            {
                "seed": old["seed"],
                "task": old["task"],
                "arm": old["arm"],
                "run_path": old["run_path"],
                "previous_state": old["state"],
            }
        )
    m["seed_amendment"] = {
        "reason": "Explicit user scope reduction; completed excluded results archived unchanged"
        if reduction
        else "Explicit user seed request; excluded seed had not started; inference settings unchanged",
        "scope_reduction": reduction,
        "recorded_at": now(),
        "parent_manifest_sha256": digest(parent),
        "old_seeds": old_seeds,
        "new_seeds": new_seeds,
        "removed_unstarted_seeds": [] if reduction else sorted(removed),
        "excluded_seeds": sorted(removed) if reduction else [],
        "archived_completed_results": archived_results,
        "added_seeds": sorted(set(new_seeds) - set(old_seeds)),
        "inherited_runs": inherited,
    }
    return previous["started_at"]


def initialize(args):
    if git(
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        "src",
        "scripts",
        "configs",
        "tests",
        "uv.lock",
    ):
        raise ValueError("Commit code/settings/tests before freezing the study")
    cfg, pipeline = load_spec(args.config), read(args.pipeline)
    validate_pipeline(pipeline, cfg)
    cohort = verify_full_cohort(args, cfg)
    env = shared.collect_environment(args.gpus, cfg)
    if env["execution"]["backend"] != "vllm":
        raise ValueError("vLLM is required")
    args.study.mkdir(parents=True, exist_ok=True)
    inputs = {}
    for path in (
        args.config,
        args.pipeline,
        args.cohort_manifest,
        ROOT / "uv.lock",
        Path(__file__),
        ROOT / "scripts/shared_eval.py",
    ):
        inputs[str(path)] = file_digest(path)
    m = {
        "protocol": pipeline["protocol"],
        "code_commit": git("rev-parse", "HEAD"),
        "execution_branch": git("branch", "--show-current"),
        "source": source_fingerprint(),
        "config": cfg,
        "pipeline": pipeline,
        "cohort": cohort,
        "environment": env,
        "gpus": args.gpus,
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "historical_report": str(args.historical_report),
        "cohort_manifest": str(args.cohort_manifest),
        "native_run": str(args.native_run),
        "continuation_study": str(args.continuation_study) if args.continuation_study else None,
        "name": args.name,
        "min_free_gib": args.min_free_gib,
        "deadline_epoch": None,
        "inputs": inputs,
        "seed_configs": {},
        "id_files": {},
    }
    for seed in pipeline["seeds"]:
        clone = json.loads(json.dumps(cfg))
        clone["experiment"]["seed"] = seed
        path = args.study / "configs" / ("seed-" + str(seed) + ".json")
        atomic_json(path, clone)
        inputs[str(path)] = file_digest(path)
        m["seed_configs"][str(seed)] = str(path)
    for task, group in cohort.items():
        path = args.study / "ids" / (task + ".json")
        atomic_json(path, group["ids"])
        inputs[str(path)] = file_digest(path)
        m["id_files"][task] = str(path)
    historical, more = historical_results(args, m)
    inputs.update(more)
    jobs = list(historical)
    estimates = {(j["task"], j["arm"]): j["phase_wall_seconds"] for j in historical}
    for task in TASKS:
        for seed in pipeline["seeds"]:
            if seed == pipeline["historical_seed"]:
                continue
            for arm in pipeline["arms"]:
                run_name = "-".join((args.study.name, str(seed), task, arm))
                jobs.append(
                    {
                        "seed": seed,
                        "task": task,
                        "arm": arm,
                        "state": "queued",
                        "reused": False,
                        "n_required": cohort[task]["n"],
                        "n": 0,
                        "correct": 0,
                        "estimated_seconds": estimates[task, arm],
                        "run_path": str(args.work_dir / "outputs" / run_name),
                        "config_file": m["seed_configs"][str(seed)],
                    }
                )
    continued_start = continue_study(args, m, jobs)
    native_plan = read(args.native_run / "plan.json")
    if native_plan["source"] != m["source"] or native_plan["gpus"] != args.gpus.split(","):
        raise ValueError("Native validation source/allocation differs")
    inputs[str(args.native_run / "plan.json")] = file_digest(args.native_run / "plan.json")
    atomic_json(args.study / "manifest.json", m)
    atomic_json(args.study / "manifest-sha256.json", {"sha256": digest(m)})
    atomic_json(args.study / "environment.json", env)
    shutil.copy2(args.cohort_manifest, args.study / "cohort-manifest.json")
    return m, {
        "state": "prepared",
        "started_at": continued_start,
        "jobs": jobs,
        "preflight": {"state": "pending"},
    }


def check(args, m):
    if (
        digest(m) != read(args.study / "manifest-sha256.json")["sha256"]
        or source_fingerprint() != m["source"]
        or git("rev-parse", "HEAD") != m["code_commit"]
    ):
        raise ValueError("Frozen manifest/package/code identity changed")
    if environment() != m["environment"]["runtime"]:
        raise ValueError("Frozen runtime changed")
    for key in ("gpus", "name", "min_free_gib"):
        if getattr(args, key) != m[key]:
            raise ValueError("Frozen allocation/protocol changed: " + key)
    for key in ("work_dir", "model_cache", "historical_report", "cohort_manifest", "native_run"):
        if str(getattr(args, key)) != m[key]:
            raise ValueError("Frozen storage/provenance changed: " + key)
    for path, sha in m["inputs"].items():
        if file_digest(Path(path)) != sha:
            raise ValueError("Frozen input changed: " + path)
    continuation = str(args.continuation_study) if args.continuation_study else None
    if continuation != m.get("continuation_study"):
        raise ValueError("Continuation parent changed")
    if bool(getattr(args, "reduce_seeds", False)) != m.get("seed_amendment", {}).get(
        "scope_reduction", False
    ):
        raise ValueError("Frozen scope reduction authorization changed")


def export(study, m, state):
    summary = analyze(state, m)
    lines = [
        "# Main argmax — full six-benchmark multi-seed evaluation",
        "",
        f"Updated {now()}; state={state['state']}",
        "",
        "Same fixed argmax method for every seed/task, 32768-token cap, vLLM, identical full-v1 IDs. No seed voting or best-seed selection. Historical seed is retrospective and excluded from the primary new-seed aggregate.",
        "",
        "Seeds: "
        + ", ".join(map(str, m["pipeline"]["seeds"]))
        + "; historical seed: "
        + str(m["pipeline"]["historical_seed"])
        + ".",
        "",
        "## Primary: newly measured seeds only",
        "",
        "| Dataset | Full n | Audited seed pairs | AR mean ± SD (%) | Ours mean ± SD (%) | Delta mean ± SD (pp) | Positive seeds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    def fmt(stats):
        if stats["mean"] is None:
            return "pending"
        return f"{stats['mean']:.2f}" + (
            f" ± {stats['sample_sd']:.2f}" if stats["sample_sd"] is not None else " (SD pending)"
        )

    required = len(m["pipeline"]["seeds"]) - 1
    for task in TASKS:
        s = summary[task]["prospective"]
        lines.append(
            f"| {task} | {m['cohort'][task]['n']} | {s['seeds']}/{required} | {fmt(s['baseline_accuracy'])} | {fmt(s['ours_accuracy'])} | {fmt(s['delta_pp'])} | {s['positive_seeds']}/{s['seeds']} |"
        )
    lines += [
        "",
        "## Per-seed full-set coverage",
        "",
        "| Dataset | Seed | Cohort | AR correct/completed/required | Ours correct/completed/required | Delta pp | State |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for task in TASKS:
        for seed in m["pipeline"]["seeds"]:
            js = {j["arm"]: j for j in state["jobs"] if j["task"] == task and j["seed"] == seed}
            b, o = js["baseline"], js["ours"]
            complete = all(j["state"] == "complete" and j.get("audits_passed") for j in js.values())
            delta = (
                f"{100 * (o['correct'] - b['correct']) / b['n']:+.2f}" if complete else "pending"
            )
            kind = "historical/reused" if seed == m["pipeline"]["historical_seed"] else "new"
            lines.append(
                f"| {task} | {seed} | {kind} | {b['correct']}/{b['n']}/{b['n_required']} | {o['correct']}/{o['n']}/{o['n_required']} | {delta} | AR={b['state']}, ours={o['state']} |"
            )
    new = [j for j in state["jobs"] if not j["reused"]]
    state["new_conditions_completed"] = sum(j["state"] == "complete" for j in new)
    state["new_conditions_required"] = len(new)
    remaining = sum(
        j["estimated_seconds"] for j in new if j["state"] not in ("complete", "running")
    )
    for j in new:
        if j["state"] == "running":
            remaining += max(
                0,
                j["estimated_seconds"]
                - (time.time() - datetime.fromisoformat(j["started_at"]).timestamp()),
            )
    state["historical_phase_estimate_remaining_hours"] = remaining / 3600
    lines += [
        "",
        f"New conditions: {state['new_conditions_completed']}/{len(new)} complete; historical conditions: {sum(j['reused'] for j in state['jobs'])} reused. Initial/remaining phase-time estimate from historical timings: {remaining / 3600:.1f} hours; model initialization, audits and seed-dependent trace lengths add uncertainty.",
        "",
        "Native GPU validation: " + json.dumps(state["preflight"], sort_keys=True),
        "",
        "Each new AR result is audited and sealed once before its same-seed ours run. Checkpoints and absolute deadlines remain immutable on resume; all runs have no wall-time cutoff. Partial conditions never contribute to seed aggregates. SD is sample SD across seed accuracies/differences, not token-level variation. All datasets and regressions are retained.",
        "",
    ]
    atomic_json(study / "status.json", state)
    atomic_json(study / "summary.json", summary)
    atomic_text(study / "results.md", "\n".join(lines))


def assert_worker_audits(run, plan, m):
    for assignment in plan["workers"]:
        worker = run / "workers" / assignment["name"]
        identity = read(worker / "identity.json")
        audit = read(worker / "audit.json")
        split = read(worker / "split.json")
        expected = sum(len(v["evaluation"]) for v in split["tasks"].values())
        if (
            identity["source"] != m["source"]
            or identity["environment"] != m["environment"]["runtime"]
            or audit.get("partial")
            or audit["completed_cases"] != expected
            or audit["completed_conditions"] != expected
        ):
            raise ValueError("Worker audit/runtime/coverage differs")


def native_gate(args, m, state):
    run = args.native_run
    plan = read(run / "plan.json")
    expected = [
        i for t in ("gsm8k", "mmlu") for i in m["cohort"][t]["ids"][: len(m["gpus"].split(","))]
    ]
    if (
        plan["source"] != m["source"]
        or plan["gpus"] != m["gpus"].split(",")
        or plan["benchmarks"] != ["gsm8k", "mmlu"]
        or plan["arms"] != ["baseline", "ours"]
        or plan["seconds_per_arm"] is not None
        or plan["smoke"]
        or plan["limit"] is not None
        or set(plan["ids"]) != set(expected)
        or len(plan["ids"]) != len(expected)
    ):
        raise ValueError("Native GPU validation protocol differs")
    while True:
        status = read(run / "status.json")
        _, _, out = collect(run)
        state["preflight"] = {
            "state": status["state"],
            "completed": sum(len(v) for v in out.values()),
            "required": 2 * len(expected),
            "benchmark_scores": False,
        }
        export(args.study, m, state)
        if status["state"] == "complete" and status.get("audits_passed"):
            break
        if status["state"] in ("failed", "interrupted", "budget_exhausted"):
            raise RuntimeError("Native validation stopped; resume its original run first")
        print("NATIVE", state["preflight"], flush=True)
        time.sleep(15)
    assert_worker_audits(run, plan, m)
    for arm, records in out.items():
        if len(records) != len(expected) or {r["id"] for r in records.values()} != set(expected):
            raise ValueError("Native validation lacks required IDs")
        for task in ("gsm8k", "mmlu"):
            rows = [r for r in records.values() if r["task"] == task]
            if sum(r["prediction"] is not None for r in rows) < 0.9 * len(rows):
                raise ValueError("Native validation lacks extracted final answers")
    if sum(r["events"] for r in out["ours"].values()) < 1:
        raise ValueError("Native validation did not exercise branch memory")
    state["preflight"].update(
        state="complete",
        audits_passed=True,
        extracted_finals=sum(r["prediction"] is not None for v in out.values() for r in v.values()),
        ours_events=sum(r["events"] for r in out["ours"].values()),
    )
    export(args.study, m, state)


def validate_job_run(job, m, args, complete=False):
    run = Path(job["run_path"])
    plan = read(run / "plan.json")
    ids = m["cohort"][job["task"]]["ids"]
    if (
        plan["source"] != m["source"]
        or plan["gpus"] != m["gpus"].split(",")
        or plan["arms"] != [job["arm"]]
        or plan["benchmarks"] != [job["task"]]
        or plan["seconds_per_arm"] is not None
        or plan["smoke"]
        or plan["limit"] is not None
        or plan["counts"] != {job["task"]: len(ids)}
        or len(plan["ids"]) != len(ids)
        or set(plan["ids"]) != set(ids)
    ):
        raise ValueError("Run identity/seed cohort/allocation differs")
    cfg = runtime_spec(load_spec(job["config_file"]), args.work_dir, args.model_cache)
    if cfg["experiment"]["seed"] != job["seed"]:
        raise ValueError("Run seed differs")
    expected = json.loads(json.dumps(cfg))
    expected["experiment"]["arms"] = [
        "plain_ar" if job["arm"] == "baseline" else "filtered_futures"
    ]
    expected["execution"]["development_cases_per_task"] = 0
    expected["datasets"] = [{"name": job["task"]}]
    expected["smoke"] = {"tasks": [job["task"]], "cases_per_task": 1}
    prepared = load_prepared(args.work_dir, cfg, job["task"])
    for index, w in enumerate(plan["workers"]):
        if read(run / w["config"]) != expected:
            raise ValueError("Frozen worker config differs")
        wanted = {
            "tasks": {
                job["task"]: {
                    "development": [],
                    "evaluation": prepared[index :: len(plan["workers"])],
                }
            }
        }
        if read(run / w["split"]) != wanted:
            raise ValueError("Frozen worker shard differs")
    if complete:
        status = read(run / "status.json")
        if status["state"] != "complete" or not status.get("audits_passed"):
            raise ValueError("Run has not completed all audits")
        assert_worker_audits(run, plan, m)
    return plan


def current_rows(job):
    _, _, all_rows = collect(Path(job["run_path"]))
    records = list(all_rows[job["arm"]].values())
    if any(r["task"] != job["task"] or r["arm"] != job["arm"] for r in records):
        raise ValueError("Unexpected arm/task in outcomes")
    records.sort(key=lambda r: r["id"])
    return records


def refresh_job(job):
    records = current_rows(job)
    job.update(
        n=len(records),
        correct=sum(r["correct"] for r in records),
        missing_finals=sum(r["prediction"] is None for r in records),
        body_tokens=sum(r["body_tokens"] for r in records),
        fork_events=sum(r["events"] for r in records),
    )
    return records


def baseline_for(state, seed, task):
    job = next(
        j
        for j in state["jobs"]
        if j["seed"] == seed and j["task"] == task and j["arm"] == "baseline"
    )
    if job["state"] != "complete" or not job.get("audits_passed"):
        raise ValueError("Complete and freeze matched baseline before ours")
    saved = read(Path(job["reference_file"]))
    if (
        saved["sha256"] != digest(saved["payload"])
        or saved["sha256"] != job["reference_sha256"]
        or saved["payload"]["seed"] != seed
        or saved["payload"]["task"] != task
        or saved["payload"]["n"] != job["n"]
        or saved["payload"]["correct"] != job["correct"]
    ):
        raise ValueError("Frozen matched baseline changed")
    return saved


def finish_job(args, m, state, job):
    run = Path(job["run_path"])
    validate_job_run(job, m, args, True)
    records = refresh_job(job)
    group = m["cohort"][job["task"]]
    if len(records) != group["n"] or {r["id"] for r in records} != set(group["ids"]):
        raise ValueError("Complete job lacks full required IDs")
    phase = read(run / "schedule.json")[job["arm"]]
    end = read(run / (job["arm"] + "-complete.json"))["at"]
    seconds = datetime.fromisoformat(end).timestamp() - phase["start_epoch"]
    target = args.study / "outcomes" / str(job["seed"]) / (job["task"] + "-" + job["arm"] + ".json")
    if target.exists() and read(target) != records:
        raise ValueError("Completed outcome artifact changed")
    if not target.exists():
        atomic_json(target, records)
    job.update(
        finished_at=end,
        phase_wall_seconds=seconds,
        outcomes_file=str(target),
        outcomes_sha256=digest(records),
    )
    if job["arm"] == "baseline":
        payload = {
            "seed": job["seed"],
            "task": job["task"],
            "n": len(records),
            "correct": job["correct"],
            "outcomes": records,
            "source": m["source"],
            "code_commit": m["code_commit"],
            "config": load_spec(job["config_file"]),
            "environment": m["environment"],
            "cohort_manifest_sha256": file_digest(args.cohort_manifest),
            "cohort_ids_sha256": digest(group["ids"]),
            "source_run_plan_sha256": file_digest(run / "plan.json"),
            "finished_at": end,
            "phase_wall_seconds": seconds,
            "deadline_epoch": None,
        }
        path = args.study / "baselines" / str(job["seed"]) / (job["task"] + ".json")
        sha = seal_reference(path, payload)
        job.update(reference_file=str(path), reference_sha256=sha)
    else:
        ref = baseline_for(state, job["seed"], job["task"])
        pair = paired_summary(
            {r["id"]: r for r in ref["payload"]["outcomes"]}, {r["id"]: r for r in records}
        )
        job.update(
            gains=pair["gains"], losses=pair["losses"], baseline_reference_sha256=ref["sha256"]
        )
    job.update(state="complete", audits_passed=True)
    export(args.study, m, state)
    print(
        "COMPLETE", job["seed"], job["task"], job["arm"], job["correct"], "/", job["n"], flush=True
    )


def supervisor_busy(run):
    with (run / "supervisor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False
        except BlockingIOError:
            return True


def retire_stopped_parent(parent, replacement, proc=Path("/proc")):
    """Retire only a stopped old scheduler after its GPU child has finished."""
    retired = []
    for path in proc.iterdir():
        if not path.name.isdigit():
            continue
        try:
            command = (path / "cmdline").read_bytes().split(b"\0")
            if not command or not Path(command[0].decode()).name.startswith("python"):
                continue
            if not any(p.endswith(b"/run_multiseed_argmax.py") for p in command):
                continue
            if b"--study" not in command or b"run" not in command:
                continue
            position = command.index(b"--study") + 1
            if command[position] != str(parent).encode():
                continue
            state = next(
                line
                for line in (path / "status").read_text().splitlines()
                if line.startswith("State:")
            )
            if state.split()[1] not in ("T", "t"):
                raise RuntimeError("Previous scheduler is still active; do not run two schedulers")
            os.kill(int(path.name), signal.SIGKILL)
            retired.append(int(path.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    atomic_json(
        parent / "superseded.json",
        {
            "replacement_study": str(replacement),
            "at": now(),
            "retired_scheduler_pids": retired,
            "reason": "User requested a seed scope amendment; frozen inputs and GPU work preserved",
        },
    )


def await_continued_run(args, m, state, job):
    if "continued_from" not in job:
        return
    run = Path(job["run_path"])
    while supervisor_busy(run):
        status = read(run / "status.json")
        if status["state"] in ("failed", "interrupted", "budget_exhausted"):
            raise RuntimeError("Inherited run stopped; original checkpoints preserved")
        job.update(state="running", started_at=job.get("started_at") or now())
        state["state"] = "running"
        refresh_job(job)
        export(args.study, m, state)
        print(
            "CONTINUING",
            job["seed"],
            job["task"],
            job["arm"],
            job["n"],
            "/",
            job["n_required"],
            flush=True,
        )
        time.sleep(15)
    retire_stopped_parent(Path(job["continued_from"]["study"]), args.study)


def run_job(args, m, state, job):
    if job["arm"] == "ours":
        baseline_for(state, job["seed"], job["task"])
    await_continued_run(args, m, state, job)
    shared.require_free_gpus(args.gpus)
    run = Path(job["run_path"])
    if not run.exists():
        cfg = runtime_spec(load_spec(job["config_file"]), args.work_dir, args.model_cache)
        create_run(
            args.work_dir,
            cfg,
            [job["task"]],
            gpus=args.gpus,
            arms=[job["arm"]],
            run_name=run.name,
            ids=m["cohort"][job["task"]]["ids"],
            ids_file=Path(m["id_files"][job["task"]]),
        )
    validate_job_run(job, m, args)
    if read(run / "status.json")["state"] == "complete":
        finish_job(args, m, state, job)
        return
    job.update(state="running", started_at=job.get("started_at") or now())
    state.update(state="running", started_at=state["started_at"] or now())
    export(args.study, m, state)
    cmd = [
        str(args.uv),
        "run",
        "--frozen",
        "python",
        "-u",
        "-m",
        "lost_tokens",
        "resume",
        "--run",
        str(run),
    ]
    job.setdefault("commands", []).append(cmd)
    log = args.study / "logs" / (str(job["seed"]) + "-" + job["task"] + "-" + job["arm"] + ".log")
    log.parent.mkdir(exist_ok=True)
    with log.open("a") as stream:
        child = subprocess.Popen(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                refresh_job(job)
                export(args.study, m, state)
                print(
                    "PROGRESS",
                    job["seed"],
                    job["task"],
                    job["arm"],
                    job["n"],
                    "/",
                    job["n_required"],
                    flush=True,
                )
                if shutil.disk_usage(args.work_dir).free < args.min_free_gib * 1024**3:
                    raise RuntimeError(
                        "Storage reserve reached; stopping owned run with checkpoints preserved"
                    )
                time.sleep(15)
            if child.returncode != 0:
                raise RuntimeError(
                    "Child run failed; original checkpoint identities retained: " + str(log)
                )
        finally:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
            try:
                child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                # Stop only workers launched by this owned child if graceful
                # cleanup failed; never touch unrelated GPU processes.
                launch = read_json(run / "launch.json", {})
                if launch.get("pid") == child.pid:
                    for pid in launch.get("worker_pids", {}).values():
                        try:
                            command = Path("/proc", str(pid), "cmdline").read_bytes().split(b"\0")
                            if b"_worker" in command and str(run).encode() in command:
                                os.kill(pid, signal.SIGINT)
                        except (FileNotFoundError, ProcessLookupError):
                            pass
                child.kill()
                child.wait()
    finish_job(args, m, state, job)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "report"))
    for name in (
        "study",
        "work-dir",
        "model-cache",
        "shared",
        "cohort-manifest",
        "historical-report",
        "native-run",
        "uv",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/vllm-argmax.json")
    parser.add_argument("--pipeline", type=Path, default=ROOT / "configs/multiseed-argmax.json")
    parser.add_argument("--continuation-study", type=Path)
    parser.add_argument("--reduce-seeds", action="store_true")
    parser.add_argument("--gpus", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--min-free-gib", type=float, default=32)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    if args.min_free_gib <= 0:
        raise ValueError("Positive storage reserve required")
    args.study.mkdir(parents=True, exist_ok=True)
    install_interrupt_handlers()
    with (args.study / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (args.study / "manifest.json").exists():
            m, state = read(args.study / "manifest.json"), read(args.study / "status.json")
        else:
            m, state = initialize(args)
        check(args, m)
        if args.action != "run" or state["state"] == "complete":
            export(args.study, m, state)
            return
        current = None
        try:
            state.update(state="validating", started_at=state["started_at"] or now())
            native_gate(args, m, state)
            for job in state["jobs"]:
                current = job
                if job["state"] == "complete":
                    if job["arm"] == "baseline":
                        baseline_for(state, job["seed"], job["task"])
                    continue
                check(args, m)
                run_job(args, m, state, job)
            branch = f"{args.name}-{datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()}"
            if git("branch", "--show-current") != branch:
                subprocess.run(["git", "branch", "-m", branch], cwd=ROOT, check=True)
            state.update(state="complete", finished_at=now(), result_branch=branch)
        except BaseException as exc:
            state.update(
                state="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                error=traceback.format_exc(),
            )
            if current and current["state"] != "complete":
                current["state"] = state["state"]
            raise
        finally:
            export(args.study, m, state)


if __name__ == "__main__":
    main()
