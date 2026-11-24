"""Frozen-baseline, resumable EM-INF study on all six committed full cohorts."""

import argparse
from datetime import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import traceback
from zoneinfo import ZoneInfo

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json, atomic_text, digest, file_digest, source_fingerprint
from lost_tokens.eminf import policy
from lost_tokens.runtime import environment, install_interrupt_handlers

ROOT = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location(
    "em_study_helpers", ROOT / "scripts/run_latent_study.py"
)
helpers = importlib.util.module_from_spec(module)
module.loader.exec_module(helpers)
read, now, git, outcomes = helpers.read, helpers.now, helpers.git, helpers.outcomes
shared = helpers.shared
TASKS = ("aime25", "hmmt25", "gpqa", "gsm8k", "math500", "mmlu")


def compatible_baseline(parent, cfg, source, runtime, gpus, lock_hash):
    """Permit EM-INF additions, not changes to any original generation component."""
    if parent["environment"]["runtime"] != runtime or parent["gpus"] != gpus:
        raise ValueError("Baseline runtime/GPU allocation differs")
    for key, value in parent["source"].items():
        if (
            key not in ("lost_tokens/config.py", "lost_tokens/default.json")
            and source.get(key) != value
        ):
            raise ValueError("Baseline generation/scoring/seed source differs: " + key)
    old_locks = [v for k, v in parent["inputs"].items() if k.endswith("/uv.lock")]
    if old_locks != [lock_hash]:
        raise ValueError("Baseline dependency lock differs")
    old = {k: v for k, v in parent["config"].items() if k not in ("latent_reasoning", "em_inf")}
    new = {k: v for k, v in cfg.items() if k not in ("latent_reasoning", "em_inf")}
    if old != new:
        raise ValueError("Baseline generator/sampler/prompt/budget configuration differs")


def validate_reference(item, task, cohort, job, parent):
    payload = item["payload"]
    rows = {r["id"]: r for r in payload["outcomes"]}
    if (
        item["sha256"] != digest(payload)
        or payload["task"] != task
        or payload["source"] != parent["source"]
        or payload["code_commit"] != parent["code_commit"]
        or payload["config"] != parent["config"]
        or payload["environment"] != parent["environment"]
        or len(rows) != payload["n"]
        or len(rows) != cohort["n"]
        or set(rows) != set(cohort["ids"])
        or payload["correct"] != sum(r["correct"] for r in rows.values())
        or not all(
            r["task"] == task and r["mode"] == "ar" and r.get("audits_passed")
            for r in rows.values()
        )
        or payload["cohort_ids_sha256"] != digest(cohort["ids"])
        or payload["cohort_manifest_sha256"] != cohort["manifest_sha256"]
        or job["state"] != "complete"
        or not job.get("audits_passed")
        or job["outcomes_sha256"] != digest([rows[i] for i in sorted(rows)])
    ):
        raise ValueError("Frozen baseline identity/coverage/audit differs: " + task)
    return payload


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
        raise ValueError("Commit execution code/settings/tests before freezing")
    cfg = load_spec(args.config)
    pol = policy(cfg)
    if (
        cfg["model"].get("backend") != "vllm"
        or not cfg["model"].get("vllm_enforce_eager")
        or cfg["model"].get("vllm_prefix_caching", True)
    ):
        raise ValueError("Keep the matched eager/no-prefix-cache vLLM engine")
    source, runtime = source_fingerprint(), environment()
    parent = read(args.baseline_study / "manifest.json")
    previous = read(args.baseline_study / "status.json")
    if (
        previous["state"] != "complete"
        or digest(parent) != read(args.baseline_study / "manifest-sha256.json")["sha256"]
    ):
        raise ValueError("Baseline study is incomplete or its identity changed")
    compatible_baseline(parent, cfg, source, runtime, args.gpus, file_digest(ROOT / "uv.lock"))
    # The only changes to old package files are new policy defaults and their
    # validation. All preexisting defaults and all generative modules are exact.
    original_defaults = json.loads(
        git("show", parent["code_commit"] + ":src/lost_tokens/default.json")
    )
    defaults = read(ROOT / "src/lost_tokens/default.json")
    if {k: v for k, v in defaults.items() if k != "em_inf"} != original_defaults:
        raise ValueError("Preexisting protocol defaults changed")
    original_validation = git("show", parent["code_commit"] + ":src/lost_tokens/config.py")
    expected_validation = original_validation.replace(
        "def validate_spec(spec):",
        'def validate_spec(spec):\n    if "em_inf" in spec:\n        from .eminf import policy as em_policy\n\n        em_policy(spec)',
    )
    if (ROOT / "src/lost_tokens/config.py").read_text().strip() != expected_validation.strip():
        raise ValueError("Preexisting configuration validation changed")
    devices = args.gpus.split(",")
    if len(devices) != len(set(devices)):
        raise ValueError("Duplicate allocated GPU")
    args.study.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.config, args.study / "config.json")
    cohort, baseline, jobs, inputs = {}, {}, [], {}
    for task in TASKS:
        ids, _, sha, version = shared.frozen_cohort(
            args.work_dir, cfg, task, args.shared, args.cohort_manifest
        )
        cohort[task] = {"ids": ids, "n": len(ids), "manifest_sha256": sha, "version": version}
        old_job = next(
            j
            for j in previous["jobs"]
            if j["stage"] == "evaluation" and j["task"] == task and j["mode"] == "ar"
        )
        ref = args.baseline_study / "baselines" / (task + ".json")
        baseline[task] = validate_reference(read(ref), task, cohort[task], old_job, parent)
        destination = args.study / "baselines" / ref.name
        destination.parent.mkdir(exist_ok=True)
        shutil.copy2(ref, destination)
        inputs[str(ref)] = file_digest(ref)
        inputs[str(destination)] = file_digest(destination)
        for stage in ("preflight", "evaluation"):
            if stage == "preflight" and task not in ("gsm8k", "mmlu"):
                continue
            selected = ids[: args.preflight_per_gpu * len(devices)] if stage == "preflight" else ids
            run = args.study / "runs" / f"{stage}-{task}-eminf"
            run.mkdir(parents=True)
            workers = []
            for index, gpu in enumerate(devices):
                assigned = selected[index :: len(devices)]
                path = run / f"ids-worker{index}.json"
                atomic_json(path, assigned)
                inputs[str(path)] = file_digest(path)
                workers.append(
                    {
                        "gpu": gpu,
                        "n": len(assigned),
                        "ids_file": str(path),
                        "path": str(run / f"worker{index}"),
                    }
                )
            jobs.append(
                {
                    "stage": stage,
                    "task": task,
                    "mode": "eminf",
                    "state": "queued",
                    "run": str(run),
                    "workers": workers,
                    "n_required": len(selected),
                }
            )
    jobs.sort(key=lambda j: 0 if j["stage"] == "preflight" else 1)
    for path in (
        args.config,
        args.study / "config.json",
        args.cohort_manifest,
        ROOT / "uv.lock",
        Path(__file__),
        ROOT / "scripts/run_latent_study.py",
        ROOT / "scripts/run_verification_study.py",
        ROOT / "scripts/shared_eval.py",
        args.baseline_study / "manifest.json",
        args.baseline_study / "manifest-sha256.json",
        args.baseline_study / "status.json",
    ):
        inputs[str(path)] = file_digest(path)
    env = shared.shared.collect_environment(args.gpus, cfg)
    manifest = {
        "protocol": "eminf-full-frozen-ar-v1",
        "code_commit": git("rev-parse", "HEAD"),
        "execution_branch": git("branch", "--show-current"),
        "source": source,
        "config": cfg,
        "config_file": str(args.study / "config.json"),
        "policy": pol,
        "cohort": cohort,
        "baseline": baseline,
        "baseline_study": str(args.baseline_study),
        "baseline_code_commit": parent["code_commit"],
        "baseline_timing": "original completed measurements, not rerun or added to current elapsed time",
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
    helpers.check(args, m)
    if str(args.baseline_study) != m["baseline_study"]:
        raise ValueError("Resume baseline provenance changed")


def export(study, m, state):
    lines = [
        "# EM-INF — all six full cohorts, frozen matched AR",
        "",
        f"Updated {now()}; state={state['state']}",
        "",
        "One transformer trajectory and one final answer. FP32 logit-only Adam (3 steps; lr 0.1; entropy threshold 0.3; reverse-KL weight 0.05), then unchanged temperature 0.6 / top-k 20 / top-p 0.95 and repetition guard. No SeLaR, rollouts, verifier, prompt edits or budget forcing. Original AR reference reused unchanged.",
        "",
        "| Dataset | Full n | Frozen AR | EM-INF | Δ correct | Gains / losses | State |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for job in state["jobs"]:
        rs = outcomes(job)
        job.update(
            n=len(rs),
            correct=sum(r["correct"] for r in rs.values()),
            missing=sum(r["prediction"] is None for r in rs.values()),
            optimized_tokens=sum(r["optimized_tokens"] for r in rs.values()),
            body_tokens=sum(r["body_tokens"] for r in rs.values()),
        )
        if job["stage"] != "evaluation":
            continue
        b = m["baseline"][job["task"]]
        br = {r["id"]: r for r in b["outcomes"]}
        if not set(rs) <= set(br):
            raise ValueError("Unexpected EM-INF evaluation IDs")
        job.update(
            gains=sum(r["correct"] and not br[i]["correct"] for i, r in rs.items()),
            losses=sum(not r["correct"] and br[i]["correct"] for i, r in rs.items()),
        )
        score = (
            f"{job['correct']}/{job['n']} ({100 * job['correct'] / job['n']:.2f}%)"
            if job["n"]
            else "pending"
        )
        delta = str(job["correct"] - b["correct"]) if job["state"] == "complete" else "pending"
        lines.append(
            f"| {job['task']} | {b['n']} | {b['correct']}/{b['n']} ({100 * b['correct'] / b['n']:.2f}%) | {score} | {delta} | {job['gains']} / {job['losses']} | {job['state']} |"
        )
    lines += [
        "",
        "## Native GPU preflights — excluded from benchmark scores",
        "",
        "| Dataset | Complete | Required | Extracted finals | Optimized tokens | State |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for j in state["jobs"]:
        if j["stage"] == "preflight":
            lines.append(
                f"| {j['task']} | {j['n']} | {j['n_required']} | {j['n'] - j['missing']} | {j['optimized_tokens']} | {j['state']} |"
            )
    lines += [
        "",
        "All six full-v1 cohorts are required. Preflights must pass native answer extraction and optimizer audits before official generation. Completed case files, optimizer metadata and hash-chained 128-token checkpoints are immutable. Resume reconstructs saved discrete KV inputs one decode step at a time; future outputs under dynamic batching are not promised bitwise identical. Baseline timings belong to their original study. Partial scores are provisional; all regressions and missing finals are retained.",
        "",
    ]
    atomic_json(study / "status.json", state)
    atomic_text(study / "results.md", "\n".join(lines))


def run_job(args, m, state, job):
    shared.shared.require_free_gpus(args.gpus)
    job.update(state="running", started_at=job.get("started_at") or now())
    state.update(state="running", started_at=state["started_at"] or now())
    export(args.study, m, state)
    processes, streams = [], []
    try:
        for index, w in enumerate(job["workers"]):
            output = Path(w["path"])
            if not w["n"] or (
                (output / "status.json").exists()
                and read(output / "status.json").get("state") == "complete"
            ):
                continue
            cmd = [
                str(args.uv),
                "run",
                "--frozen",
                "python",
                "-u",
                "-m",
                "lost_tokens.eminf_worker",
                "--config",
                m["config_file"],
                "--work-dir",
                m["work_dir"],
                "--model-cache",
                m["model_cache"],
                "--ids-file",
                w["ids_file"],
                "--output",
                str(output),
                "--task",
                job["task"],
                "--mode",
                "eminf",
                "--source-sha256",
                digest(m["source"]),
                "--uv-lock-sha256",
                m["inputs"][str(ROOT / "uv.lock")],
            ]
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = w["gpu"]
            env["PYTORCH_CUDA_ALLOC_CONF"] = m["config"]["model"]["cuda_allocator_config"]
            stream = (Path(job["run"]) / f"worker{index}.log").open("a")
            streams.append(stream)
            processes.append(
                subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
            )
            w.setdefault("commands", []).append(cmd)
        while any(p.poll() is None for p in processes):
            if any(p.poll() not in (None, 0) for p in processes):
                raise RuntimeError("EM-INF worker failed; checkpoints preserved")
            export(args.study, m, state)
            print(
                "PROGRESS", job["stage"], job["task"], job["n"], "/", job["n_required"], flush=True
            )
            time.sleep(15)
        if any(p.returncode != 0 for p in processes):
            raise RuntimeError("EM-INF worker failure")
        for w in job["workers"]:
            if not w["n"]:
                continue
            ws = read(Path(w["path"]) / "status.json")
            if (
                ws["state"] != "complete"
                or not ws.get("audits_passed")
                or ws["n"] != w["n"]
                or ws["engine_metrics"]["soft_inputs_applied"] != 0
            ):
                raise ValueError("EM-INF worker coverage/audit/embedding invariant failed")
        found = outcomes(job)
        expected = set(i for w in job["workers"] for i in read(w["ids_file"]))
        if set(found) != expected or len(found) != job["n_required"]:
            raise ValueError("EM-INF condition coverage differs")
        if job["stage"] == "preflight" and (
            sum(r["prediction"] is not None for r in found.values()) < job["n_required"] * 0.9
            or sum(r["optimized_tokens"] for r in found.values()) < 1
        ):
            raise ValueError("Native preflight lacked final answers or real optimizer steps")
        job.update(
            state="complete",
            finished_at=now(),
            audits_passed=True,
            outcomes_sha256=digest([found[i] for i in sorted(found)]),
        )
        export(args.study, m, state)
        print("COMPLETE", job["stage"], job["task"], job["correct"], "/", job["n"], flush=True)
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
    for name in (
        "study",
        "work-dir",
        "model-cache",
        "shared",
        "config",
        "cohort-manifest",
        "uv",
        "baseline-study",
    ):
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
                    continue
                if job["stage"] == "evaluation" and not all(
                    j["state"] == "complete" and j.get("audits_passed")
                    for j in state["jobs"]
                    if j["stage"] == "preflight"
                ):
                    raise ValueError("Native preflights must pass before benchmark generation")
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
