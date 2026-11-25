"""Complete five argmax cohorts before resuming the existing MMLU queue.

Only orchestration changes. Completed references are imported by identity,
never selected by score; all new generation uses the unchanged native preset.
"""

import argparse
import copy
from datetime import datetime
import fcntl
import importlib.util
from pathlib import Path
import shlex
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
TASKS = ("aime25", "hmmt25", "gpqa", "gsm8k", "math500")
read, now = base.read, base.now
original_export = base.export


def export(study, m, state):
    original_export(study, m, state)
    path = study / "results.md"
    content = path.read_text().replace(
        "# Main argmax — full six-benchmark multi-seed evaluation",
        "# Argmax — five full benchmarks; MMLU deferred",
    )
    atomic_text(path, content)
    atomic_text(study / "ours.md", content)


base.export = export


def validate_protocol(pipeline, cfg):
    if (
        pipeline["protocol"] != "argmax-five-benchmarks-priority-v1"
        or tuple(pipeline["benchmarks"]) != TASKS
        or len(pipeline["seeds"]) != 5
        or len(set(pipeline["seeds"])) != 5
        or any(type(seed) is not int for seed in pipeline["seeds"])
        or pipeline["historical_seed"] != cfg["experiment"]["seed"]
        or pipeline["historical_seed"] not in pipeline["seeds"]
        or pipeline["method"] != "filtered_futures/argmax"
        or pipeline["arms"] != ["baseline", "ours"]
        or pipeline["cohort"] != "full-v1"
    ):
        raise ValueError(
            "Require five fixed seeds and exactly the five full cohorts excluding MMLU"
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
    validate_protocol(pipeline, cfg)
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
            args.resume_request,
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
        "resume_request": str(args.resume_request),
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


def resume_previous(args):
    request = read(args.resume_request)
    cwd = Path(request["cwd"])
    if (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip()
        != request["code_commit"]
    ):
        raise ValueError("Original MMLU resume checkout changed")
    log = Path(request["argv"][request["argv"].index("--study") + 1]) / "controller.log"
    command = shlex.join(request["argv"]) + " >> " + shlex.quote(str(log)) + " 2>&1"
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", args.resume_session, "-c", str(cwd), command],
        check=True,
    )
    atomic_json(
        args.study / "mmlu-resumed.json",
        {"at": now(), "request": str(args.resume_request), "session": args.resume_session},
    )


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
        "resume-request",
        "uv",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-study", type=Path, action="append", required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/vllm-argmax.json")
    parser.add_argument(
        "--pipeline", type=Path, default=ROOT / "configs/argmax-five-benchmarks.json"
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--gpus", required=True)
    parser.add_argument("--resume-session", required=True)
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
        if str(args.resume_request) != m["resume_request"]:
            raise ValueError("Original MMLU resume request changed")
        if args.action != "run" or state["state"] == "complete":
            export(args.study, m, state)
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
        resume_previous(args)


if __name__ == "__main__":
    main()
