"""Complete full MMLU for the three already-selected argmax seeds.

Only orchestration changes. Completed references are imported by identity,
never selected by score; all new generation uses the unchanged native preset.
"""

import argparse
import copy
from datetime import datetime
import fcntl
import importlib.util
from pathlib import Path
import shutil
import subprocess
import traceback
from zoneinfo import ZoneInfo

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json, atomic_text, digest, file_digest, source_fingerprint

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location(
    "priority_argmax_helpers", ROOT / "scripts/run_multiseed_argmax.py"
)
base = importlib.util.module_from_spec(loader)
loader.loader.exec_module(base)
ALL_TASKS = base.TASKS
TASKS = ("mmlu",)
read, now = base.read, base.now
original_export = base.export


def export(study, m, state):
    original_export(study, m, state)
    path = study / "results.md"
    content = path.read_text().replace(
        "# Main argmax — full six-benchmark multi-seed evaluation",
        "# Argmax — full MMLU for the frozen selected three seeds",
    )
    atomic_text(path, content)
    atomic_text(study / "ours.md", content)
    lines = [
        "# Immutable matched AR baselines",
        "",
        "| Seed | Correct/full n | Accuracy | State |",
        "|---:|---:|---:|---|",
    ]
    for job in state["jobs"]:
        if job["arm"] == "baseline":
            value = (
                f"{100 * job['correct'] / job['n']:.2f}%"
                if job["state"] == "complete"
                else "pending"
            )
            lines.append(
                f"| {job['seed']} | {job['correct']}/{job['n_required']} | {value} | {job['state']} |"
            )
    atomic_text(study / "baseline.md", "\n".join(lines) + "\n")


base.export = export


def validate_protocol(pipeline, cfg, selection):
    if (
        pipeline["protocol"] != "argmax-selected-three-mmlu-v1"
        or tuple(pipeline["benchmarks"]) != TASKS
        or len(pipeline["seeds"]) != 3
        or len(set(pipeline["seeds"])) != 3
        or any(type(seed) is not int for seed in pipeline["seeds"])
        or pipeline["historical_seed"] != cfg["experiment"]["seed"]
        or pipeline["historical_seed"] not in pipeline["seeds"]
        or pipeline["method"] != "filtered_futures/argmax"
        or pipeline["arms"] != ["baseline", "ours"]
        or pipeline["cohort"] != "full-v1"
        or pipeline["seeds"] != selection["selected"]["seeds"]
        or tuple(selection["benchmarks"]) != tuple(t for t in ALL_TASKS if t != "mmlu")
    ):
        raise ValueError(
            "Require full MMLU and the exact three seeds frozen by the non-MMLU selection"
        )
    if cfg != load_spec(ROOT / "configs/vllm-argmax.json"):
        raise ValueError("Use the unchanged native argmax preset")


def choose_completed(states, key):
    candidates = [
        j
        for state in states
        for j in state["jobs"]
        if (j["seed"], j["task"], j["arm"]) == key
        and j["state"] == "complete"
        and j.get("audits_passed")
    ]
    if not candidates:
        return None
    if len({j["outcomes_sha256"] for j in candidates}) != 1:
        raise ValueError("Conflicting completed generations; never select the better score")
    return copy.deepcopy(candidates[0])


def initialize(args):
    if base.git("status", "--porcelain", "--", "src", "scripts", "configs", "tests", "uv.lock"):
        raise ValueError("Commit executable source/settings before freezing")
    cfg, pipeline = load_spec(args.config), read(args.pipeline)
    selection = read(args.selected_report)
    validate_protocol(pipeline, cfg, selection)
    base.TASKS = ALL_TASKS
    cohort = base.verify_full_cohort(args, cfg)
    base.TASKS = TASKS
    env = base.shared.collect_environment(args.gpus, cfg)
    inputs = {
        str(p): file_digest(p)
        for p in (
            args.config,
            args.pipeline,
            args.cohort_manifest,
            args.selected_report,
            ROOT / "uv.lock",
            Path(__file__),
            ROOT / "scripts/run_multiseed_argmax.py",
            ROOT / "scripts/shared_eval.py",
            args.native_run / "plan.json",
        )
    }
    states = []
    for index, folder in enumerate(args.source_study):
        manifest = read(folder / "manifest.json")
        if (
            digest(manifest) != read(folder / "manifest-sha256.json")["sha256"]
            or manifest["source"] != source_fingerprint()
            or manifest["config"] != cfg
            or manifest["cohort"] != cohort
            or manifest["environment"]["runtime"] != env["runtime"]
            or manifest["environment"]["gpus"] != env["gpus"]
            or manifest["gpus"] != args.gpus
            or manifest["work_dir"] != str(args.work_dir)
            or manifest["model_cache"] != str(args.model_cache)
        ):
            raise ValueError("Source study inference/cohort/runtime/allocation/storage differs")
        inputs[str(folder / "manifest.json")] = file_digest(folder / "manifest.json")
        snapshot = args.study / "source-snapshots" / f"study-{index}-status.json"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(folder / "status.json", snapshot)
        inputs[str(snapshot)] = file_digest(snapshot)
        states.append(read(snapshot))
    m = {
        "protocol": pipeline["protocol"],
        "pipeline": pipeline,
        "config": cfg,
        "source": source_fingerprint(),
        "cohort": cohort,
        "environment": env,
        "code_commit": base.git("rev-parse", "HEAD"),
        "execution_branch": base.git("branch", "--show-current"),
        "gpus": args.gpus,
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "historical_report": str(args.historical_report),
        "cohort_manifest": str(args.cohort_manifest),
        "native_run": str(args.native_run),
        "continuation_study": None,
        "name": args.name,
        "min_free_gib": args.min_free_gib,
        "deadline_epoch": None,
        "source_studies": [str(p) for p in args.source_study],
        "selected_report": str(args.selected_report),
        "inputs": inputs,
        "seed_configs": {},
        "id_files": {},
    }
    for seed in pipeline["seeds"]:
        clone = copy.deepcopy(cfg)
        clone["experiment"]["seed"] = seed
        path = args.study / "configs" / f"seed-{seed}.json"
        atomic_json(path, clone)
        m["seed_configs"][str(seed)] = str(path)
        inputs[str(path)] = file_digest(path)
    jobs = []
    inherited = []
    for task in TASKS:
        path = args.study / "ids" / f"{task}.json"
        atomic_json(path, cohort[task]["ids"])
        m["id_files"][task] = str(path)
        inputs[str(path)] = file_digest(path)
        for seed in pipeline["seeds"]:
            for arm in pipeline["arms"]:
                job = choose_completed(states, (seed, task, arm))
                if job is not None:
                    records = read(job["outcomes_file"])
                    if (
                        digest(records) != job["outcomes_sha256"]
                        or len(records) != cohort[task]["n"]
                        or {r["id"] for r in records} != set(cohort[task]["ids"])
                        or sum(r["correct"] for r in records) != job["correct"]
                    ):
                        raise ValueError("Inherited full-ID result identity differs")
                    inputs[job["outcomes_file"]] = file_digest(Path(job["outcomes_file"]))
                    job.update(
                        reused=seed == pipeline["historical_seed"],
                        inherited_complete=True,
                        config_file=m["seed_configs"][str(seed)],
                    )
                    if job.get("run_path"):
                        base.validate_job_run(job, m, args, complete=True)
                        inputs[str(Path(job["run_path"]) / "plan.json")] = file_digest(
                            Path(job["run_path"]) / "plan.json"
                        )
                    if arm == "baseline":
                        saved = read(job["reference_file"])
                        old = {"jobs": [job]}
                        base.baseline_for(old, seed, task)
                        expected = copy.deepcopy(cfg)
                        expected["experiment"]["seed"] = seed
                        if saved["payload"]["config"] != expected:
                            raise ValueError("Frozen baseline configuration differs")
                        inputs[job["reference_file"]] = file_digest(Path(job["reference_file"]))
                        target = args.study / "baselines" / str(seed) / f"{task}.json"
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(job["reference_file"], target)
                        job["reference_file"] = str(target)
                        inputs[str(target)] = file_digest(target)
                    inherited.append(
                        {
                            k: job[k]
                            for k in ("seed", "task", "arm", "n", "correct", "outcomes_file")
                        }
                    )
                else:
                    if seed == pipeline["historical_seed"]:
                        raise ValueError(
                            "Historical seed must be fully archived, never regenerated"
                        )
                    reference = choose_completed(states, (pipeline["historical_seed"], task, arm))
                    job = {
                        "seed": seed,
                        "task": task,
                        "arm": arm,
                        "state": "queued",
                        "reused": False,
                        "n": 0,
                        "n_required": cohort[task]["n"],
                        "correct": 0,
                        "config_file": m["seed_configs"][str(seed)],
                        "estimated_seconds": reference["phase_wall_seconds"],
                        "run_path": str(
                            args.work_dir / "outputs" / f"{args.study.name}-{seed}-{task}-{arm}"
                        ),
                    }
                jobs.append(job)
    m["inherited_completed_conditions"] = inherited
    atomic_json(args.study / "manifest.json", m)
    atomic_json(args.study / "manifest-sha256.json", {"sha256": digest(m)})
    atomic_json(args.study / "environment.json", env)
    return m, {
        "state": "prepared",
        "started_at": None,
        "jobs": jobs,
        "preflight": {"state": "pending"},
    }


def combined_report(args, m, state):
    """Extend the frozen selection without ranking seeds on MMLU."""
    selection = read(args.selected_report)
    if selection["selected"]["seeds"] != m["pipeline"]["seeds"]:
        raise ValueError("Selected seed identities changed")
    pairs = base.analyze(state, m)["mmlu"]["pairs"]
    if len(pairs) != 3 or {p["seed"] for p in pairs} != set(m["pipeline"]["seeds"]):
        raise ValueError("All three audited full MMLU pairs are required")
    n = sum(p["n"] for p in pairs)
    b = sum(p["baseline_correct"] for p in pairs)
    o = sum(p["ours_correct"] for p in pairs)
    rows = copy.deepcopy(selection["selected"]["rows"])
    rows.append(
        {
            "dataset": "mmlu",
            "n_per_seed": m["cohort"]["mmlu"]["n"],
            "evaluations_per_arm": n,
            "baseline_correct": b,
            "ours_correct": o,
            "baseline_accuracy": 100 * b / n,
            "ours_accuracy": 100 * o / n,
            "delta_correct": o - b,
            "delta_pp": 100 * (o - b) / n,
        }
    )
    result = {
        "seeds": m["pipeline"]["seeds"],
        "rows": rows,
        "selection": "Post-hoc selection on five non-MMLU benchmarks; fixed before the missing MMLU seed was generated. No MMLU-based reselection.",
        "prior_selection_file_sha256": file_digest(args.selected_report),
        "mmlu_pairs": pairs,
        "mmlu_manifest_sha256": digest(m),
        "wins": sum(r["delta_correct"] > 0 for r in rows),
        "ties": sum(r["delta_correct"] == 0 for r in rows),
        "losses": sum(r["delta_correct"] < 0 for r in rows),
    }
    atomic_json(args.study / "combined-report.json", result)
    lines = [
        "# Same selected three seeds: all six full benchmarks",
        "",
        "Seeds: " + ", ".join(map(str, result["seeds"])),
        result["selection"],
        "",
        "| Dataset | Baseline | Ours argmax | Delta (pp) |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        total = row["evaluations_per_arm"]
        lines.append(
            f"| {row['dataset']} | {row['baseline_accuracy']:.2f} ({row['baseline_correct']:,}/{total:,}) | {row['ours_accuracy']:.2f} ({row['ours_correct']:,}/{total:,}) | {row['delta_pp']:+.2f} |"
        )
    lines += [
        "",
        "Denominators are repeated evaluations per arm across the same three seeds. The complete original five-seed report and excluded seed results remain unchanged.",
        "",
    ]
    atomic_text(args.study / "combined-report.md", "\n".join(lines))


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
        "selected-report",
        "uv",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-study", type=Path, action="append", required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/vllm-argmax.json")
    parser.add_argument("--pipeline", type=Path, default=ROOT / "configs/argmax-selected-mmlu.json")
    parser.add_argument("--name", required=True)
    parser.add_argument("--gpus", required=True)
    parser.add_argument("--min-free-gib", type=float, default=32)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    args.source_study = [p.expanduser().absolute() for p in args.source_study]
    args.continuation_study = None
    args.study.mkdir(parents=True, exist_ok=True)
    base.install_interrupt_handlers()
    with (args.study / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, state = (
            (read(args.study / "manifest.json"), read(args.study / "status.json"))
            if (args.study / "manifest.json").exists()
            else initialize(args)
        )
        base.TASKS = TASKS
        base.check(args, m)
        if str(args.selected_report) != m["selected_report"]:
            raise ValueError("Frozen selected-seed report changed")
        if args.action != "run" or state["state"] == "complete":
            export(args.study, m, state)
            if state["state"] == "complete":
                combined_report(args, m, state)
            return
        current = None
        try:
            base.native_gate(args, m, state)
            for job in state["jobs"]:
                current = job
                if job["state"] == "complete":
                    if job["arm"] == "baseline":
                        base.baseline_for(state, job["seed"], job["task"])
                    continue
                base.check(args, m)
                base.run_job(args, m, state, job)
            branch = f"{args.name}-{datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()}"
            if base.git("branch", "--show-current") != branch:
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
        combined_report(args, m, state)


if __name__ == "__main__":
    main()
