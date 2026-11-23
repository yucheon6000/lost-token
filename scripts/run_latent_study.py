"""Audited, resumable full-six-benchmark AR versus selective latent reasoning.

The two conditions are separate measurements, never an answer ensemble. Native
GPU preflights are explicit diagnostics and excluded from benchmark reporting.
"""

import argparse
from datetime import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback
from zoneinfo import ZoneInfo
import shutil

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json, atomic_text, digest, file_digest, source_fingerprint
from lost_tokens.latent import policy
from lost_tokens.runtime import environment, install_interrupt_handlers

ROOT = Path(__file__).resolve().parents[1]
helper = importlib.util.spec_from_file_location(
    "latent_study_helpers", ROOT / "scripts/run_verification_study.py"
)
shared = importlib.util.module_from_spec(helper)
helper.loader.exec_module(shared)
TASKS = ("gsm8k", "math500", "aime25", "hmmt25", "gpqa", "mmlu")


def read(path):
    return json.loads(Path(path).read_text())


def now():
    return datetime.now().astimezone().isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


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
        raise ValueError("Commit the frozen code, configurations and tests before launch")
    cfg = load_spec(args.config)
    pol = policy(cfg)
    if (
        cfg["model"].get("backend") != "vllm"
        or not cfg["model"].get("vllm_enforce_eager")
        or cfg["model"].get("vllm_prefix_caching", True)
    ):
        raise ValueError("Latent studies require eager vLLM with token-prefix caching disabled")
    args.study.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.config, args.study / "config.json")
    config_path = args.study / "config.json"
    source = source_fingerprint()
    cohort = {}
    inputs = {}
    devices = args.gpus.split(",")
    if len(devices) != len(set(devices)):
        raise ValueError("Duplicate allocated GPU")
    jobs = []
    for task in TASKS:
        ids, path, sha, version = shared.frozen_cohort(
            args.work_dir, cfg, task, args.shared, args.cohort_manifest
        )
        cohort[task] = {"ids": ids, "n": len(ids), "manifest_sha256": sha, "version": version}
        for stage, modes in (("preflight", ("selar",)), ("evaluation", ("ar", "selar"))):
            if stage == "preflight" and task not in ("gsm8k", "mmlu"):
                continue
            selected = ids[: args.preflight_per_gpu * len(devices)] if stage == "preflight" else ids
            for mode in modes:
                run = args.study / "runs" / f"{stage}-{task}-{mode}"
                run.mkdir(parents=True)
                workers = []
                for index, gpu in enumerate(devices):
                    selected_ids = selected[index :: len(devices)]
                    path = run / f"ids-worker{index}.json"
                    atomic_json(path, selected_ids)
                    inputs[str(path)] = file_digest(path)
                    workers.append(
                        {
                            "gpu": gpu,
                            "ids_file": str(path),
                            "path": str(run / f"worker{index}"),
                            "n": len(selected_ids),
                        }
                    )
                jobs.append(
                    {
                        "stage": stage,
                        "task": task,
                        "mode": mode,
                        "state": "queued",
                        "run": str(run),
                        "workers": workers,
                        "n_required": len(selected),
                    }
                )
    jobs.sort(key=lambda j: 0 if j["stage"] == "preflight" else 1)
    for path in (
        args.config,
        config_path,
        args.cohort_manifest,
        ROOT / "uv.lock",
        Path(__file__),
        ROOT / "scripts/run_verification_study.py",
        ROOT / "scripts/shared_eval.py",
    ):
        inputs[str(path)] = file_digest(path)
    env = shared.shared.collect_environment(args.gpus, cfg)
    manifest = {
        "protocol": "selective-latent-full-v1",
        "code_commit": git("rev-parse", "HEAD"),
        "execution_branch": git("branch", "--show-current"),
        "source": source,
        "config": cfg,
        "config_file": str(config_path),
        "policy": pol,
        "cohort": cohort,
        "inputs": inputs,
        "gpus": args.gpus,
        "environment": env,
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "cohort_manifest": str(args.cohort_manifest),
        "name": args.name,
        "preflight_per_gpu": args.preflight_per_gpu,
        "deadline_epoch": None,
    }
    atomic_json(args.study / "manifest.json", manifest)
    atomic_json(args.study / "manifest-sha256.json", {"sha256": digest(manifest)})
    atomic_json(args.study / "environment.json", env)
    shutil.copy2(args.cohort_manifest, args.study / "cohort-manifest.json")
    return manifest, {"state": "prepared", "started_at": None, "jobs": jobs}


def check(args, m):
    if (
        digest(m) != read(args.study / "manifest-sha256.json")["sha256"]
        or source_fingerprint() != m["source"]
        or git("rev-parse", "HEAD") != m["code_commit"]
    ):
        raise ValueError("Latent manifest/source/code identity changed")
    if environment() != m["environment"]["runtime"]:
        raise ValueError("Frozen runtime changed")
    for key in ("gpus", "name", "preflight_per_gpu"):
        if getattr(args, key) != m[key]:
            raise ValueError("Resume allocation/protocol changed: " + key)
    for key in ("work_dir", "model_cache", "cohort_manifest"):
        if str(getattr(args, key)) != m[key]:
            raise ValueError("Resume storage/cohort changed")
    for path, sha in m["inputs"].items():
        if file_digest(Path(path)) != sha:
            raise ValueError("Frozen input changed: " + path)


def outcomes(job):
    found = {}
    for worker in job["workers"]:
        for path in (Path(worker["path"]) / "outcomes").glob("*.json"):
            row = read(path)
            if row["id"] in found or row["task"] != job["task"] or row["mode"] != job["mode"]:
                raise ValueError("Duplicate or unexpected latent outcome")
            found[row["id"]] = row
    return found


def export(study, m, state):
    for j in state["jobs"]:
        rows = outcomes(j)
        j.update(
            n=len(rows),
            correct=sum(r["correct"] for r in rows.values()),
            missing=sum(r["prediction"] is None for r in rows.values()),
            soft_tokens=sum(r["soft_tokens"] for r in rows.values()),
            body_tokens=sum(r["body_tokens"] for r in rows.values()),
        )
    lines = [
        "# Selective latent reasoning — full six-benchmark suite",
        "",
        f"Updated {now()}; state={state['state']}",
        "",
        "One model, one KV trajectory, one final answer per condition. No complete-response ensemble. Top-3 latent mixture, entropy threshold 0.5, contrastive weight 1.0; same 32768-token cap. A new matched AR reference is measured once with the same eager/no-prefix-cache engine.",
        "",
        "| Dataset | Full n | Matched AR | SeLaR | Δ correct | State |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for task in TASKS:
        jobs = {
            j["mode"]: j for j in state["jobs"] if j["stage"] == "evaluation" and j["task"] == task
        }

        def score(j):
            return (
                f"{j['correct']}/{j['n']} ({100 * j['correct'] / j['n']:.2f}%)"
                if j.get("n")
                else "pending"
            )

        ar, se = jobs["ar"], jobs["selar"]
        delta = (
            str(se["correct"] - ar["correct"])
            if ar["state"] == se["state"] == "complete"
            else "pending"
        )
        lines.append(
            f"| {task} | {m['cohort'][task]['n']} | {score(ar)} | {score(se)} | {delta} | AR={ar['state']}, SeLaR={se['state']} |"
        )
    lines += [
        "",
        "## GPU integration preflights — excluded from benchmark scores",
        "",
        "| Dataset | n | Complete | Extracted finals | Soft tokens | State |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for j in state["jobs"]:
        if j["stage"] == "preflight":
            lines.append(
                f"| {j['task']} | {j['n_required']} | {j['n']} | {j['n'] - j['missing']} | {j['soft_tokens']} | {j['state']} |"
            )
    lines += [
        "",
        "Full sizes and IDs are committed full-v1, not redrawn subsets. All results, including regressions and missing finals, are retained. Latent mixing is thinking-only; math symbols and special/termination tokens remain discrete. Completed checkpoint blocks and mixture weights are immutable. Resume replays saved inputs token by token. Fixed-batch GPU replay is tested; dynamic batching can still change future floating-point results.",
    ]
    atomic_json(study / "status.json", state)
    atomic_text(study / "results.md", "\n".join(lines) + "\n")


def seal_baseline(study, job, m):
    directory = study / "baselines"
    directory.mkdir(exist_ok=True)
    path = directory / (job["task"] + ".json")
    rows = outcomes(job)
    payload = {
        "task": job["task"],
        "n": job["n_required"],
        "correct": job["correct"],
        "outcomes": [rows[i] for i in sorted(rows)],
        "source": m["source"],
        "code_commit": m["code_commit"],
        "config": m["config"],
        "environment": m["environment"],
        "cohort_manifest_sha256": m["cohort"][job["task"]]["manifest_sha256"],
        "cohort_ids_sha256": digest(m["cohort"][job["task"]]["ids"]),
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
    }
    item = {"payload": payload, "sha256": digest(payload)}
    if path.exists():
        if read(path) != item:
            raise ValueError("Sealed AR baseline changed")
    else:
        atomic_json(path, item)


def run_job(args, m, state, job):
    shared.shared.require_free_gpus(args.gpus)
    job.update(state="running", started_at=job.get("started_at") or now())
    state.update(state="running", started_at=state["started_at"] or now())
    export(args.study, m, state)
    processes = []
    streams = []
    try:
        for index, worker in enumerate(job["workers"]):
            if not worker["n"]:
                continue
            output = Path(worker["path"])
            if (output / "status.json").exists() and read(output / "status.json").get(
                "state"
            ) == "complete":
                continue
            cmd = [
                str(args.uv),
                "run",
                "--frozen",
                "python",
                "-u",
                "-m",
                "lost_tokens.latent_worker",
                "--config",
                m["config_file"],
                "--work-dir",
                m["work_dir"],
                "--model-cache",
                m["model_cache"],
                "--ids-file",
                worker["ids_file"],
                "--output",
                str(output),
                "--task",
                job["task"],
                "--mode",
                job["mode"],
                "--source-sha256",
                digest(m["source"]),
                "--uv-lock-sha256",
                m["inputs"][str(ROOT / "uv.lock")],
            ]
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = worker["gpu"]
            env["PYTORCH_CUDA_ALLOC_CONF"] = m["config"]["model"]["cuda_allocator_config"]
            stream = (Path(job["run"]) / f"worker{index}.log").open("a")
            streams.append(stream)
            processes.append(
                subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
            )
            worker.setdefault("commands", []).append(cmd)
        while any(p.poll() is None for p in processes):
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError(
                    "A latent worker failed; preserve and resume its original identity"
                )
            export(args.study, m, state)
            print(
                "PROGRESS",
                job["stage"],
                job["task"],
                job["mode"],
                job.get("n", 0),
                "/",
                job["n_required"],
                flush=True,
            )
            time.sleep(15)
        if any(p.returncode != 0 for p in processes):
            raise RuntimeError("Latent worker failure")
        for w in job["workers"]:
            if not w["n"]:
                continue
            status = read(Path(w["path"]) / "status.json")
            if (
                status["state"] != "complete"
                or not status.get("audits_passed")
                or status["n"] != w["n"]
            ):
                raise ValueError("Worker audit/coverage is incomplete")
        found = outcomes(job)
        expected = set(i for w in job["workers"] for i in read(w["ids_file"]))
        if set(found) != expected or len(found) != job["n_required"]:
            raise ValueError("Latent condition coverage differs")
        if job["stage"] == "preflight":
            finals = sum(r["prediction"] is not None for r in found.values())
            soft = sum(r["soft_tokens"] for r in found.values())
            if finals < job["n_required"] * 0.9 or soft < 1:
                raise ValueError(
                    "Native GPU preflight lacked extracted finals or actual latent inputs"
                )
        job.update(
            state="complete",
            finished_at=now(),
            audits_passed=True,
            outcomes_sha256=digest([found[i] for i in sorted(found)]),
        )
        export(args.study, m, state)
        if job["stage"] == "evaluation" and job["mode"] == "ar":
            seal_baseline(args.study, job, m)
        print(
            "COMPLETE",
            job["stage"],
            job["task"],
            job["mode"],
            job["correct"],
            "/",
            job["n"],
            flush=True,
        )
    finally:
        for p in processes:
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
        for p in processes:
            try:
                p.wait(timeout=45)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        for stream in streams:
            stream.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "run", "report"))
    for name in ("study", "work-dir", "model-cache", "shared", "config", "cohort-manifest", "uv"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--gpus", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--preflight-per-gpu", type=int, default=2)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    if args.preflight_per_gpu < 1:
        raise ValueError("Positive native preflight size required")
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
            for job in state["jobs"]:
                current = job
                if job["state"] == "complete":
                    if job["stage"] == "evaluation" and job["mode"] == "ar":
                        seal_baseline(args.study, job, m)
                    continue
                if job["stage"] == "evaluation" and not all(
                    j["state"] == "complete" and j.get("audits_passed")
                    for j in state["jobs"]
                    if j["stage"] == "preflight"
                ):
                    raise ValueError(
                        "Native GPU preflights must pass before any benchmark generation"
                    )
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
