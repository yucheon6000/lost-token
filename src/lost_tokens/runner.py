"""Portable sequential-arm, multi-GPU execution with strict checkpoint recovery."""

from __future__ import annotations

import copy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from .core import RunStore, atomic_json, digest, file_digest, now, source_files, source_fingerprint
from .data import load_prepared
from .protocol import planned_rows
from .reporting import DEFAULT_ARMS, collect, plan_arms, read_json, report
from .runtime import environment, heartbeat, install_interrupt_handlers

ARM_CONDITIONS = {
    "baseline": "plain_ar",
    "reference": "reference_only",
    "all": "all_futures",
    "ours": "filtered_futures",
}


class DeadlineReached(Exception):
    pass


class ProbePause(Exception):
    pass


class CheckpointStore(RunStore):
    def __init__(self, *args, deadline=None, probe=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.deadline = (
            time.monotonic() + max(0, deadline - time.time()) if deadline is not None else None
        )
        self.probe = probe
        self.last_progress = 0.0
        self.initial_checkpoints = len(list((self.path / "checkpoints").glob("*.json")))

    def call(self, *args, **kwargs):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise DeadlineReached()
        result = super().call(*args, **kwargs)
        if time.monotonic() - self.last_progress >= 5 or (self.probe and self.calls >= 2):
            atomic_json(
                self.path / "progress.json",
                {
                    "epoch": time.time(),
                    "new": self.calls,
                    "reused": self.hits,
                    "checkpoint_count": self.initial_checkpoints + self.calls,
                },
            )
            self.last_progress = time.monotonic()
        if self.probe and self.calls >= 2:
            raise ProbePause()
        return result


def devices(gpus):
    if gpus == "cpu":
        return ["cpu"]
    selected = gpus.split(",")
    if (
        not selected
        or any(not re.fullmatch(r"\d+", x) for x in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("--gpus must be unique visible indices, e.g. 0 or 0,1,2,3; or cpu")
    import torch

    count = torch.cuda.device_count()
    if any(int(x) >= count for x in selected):
        raise ValueError(
            f"Requested GPUs {selected}, but only {count} visible; check CUDA_VISIBLE_DEVICES"
        )
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    return [visible.split(",")[int(x)] for x in selected] if visible else selected


def create_run(
    work_dir,
    spec,
    benchmarks,
    gpus="0",
    hours_per_arm=None,
    limit=None,
    run_name=None,
    smoke=False,
    max_output_tokens=None,
    arms=None,
    ids=None,
    ids_file=None,
):
    arms = list(arms) if arms else list(DEFAULT_ARMS)
    if len(set(arms)) != len(arms) or any(a not in ARM_CONDITIONS for a in arms):
        raise ValueError("arms must be distinct names from " + ", ".join(ARM_CONDITIONS))
    if hours_per_arm is not None and hours_per_arm <= 0:
        raise ValueError("hours-per-arm must be positive")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if ids is not None:
        ids = list(ids)
        if limit is not None:
            raise ValueError("ids and limit are mutually exclusive")
        if smoke:
            raise ValueError("ids cannot be used with a smoke run")
        if not ids or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("ids must be a non-empty list of distinct strings")
    if not benchmarks or len(set(benchmarks)) != len(benchmarks):
        raise ValueError("Choose at least one distinct benchmark")
    gpu_ids = devices(gpus)
    run_name = (
        run_name
        or ("smoke-" if smoke else "eval-")
        + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        + "-"
        + uuid.uuid4().hex[:6]
    )
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", run_name):
        raise ValueError("run-name must be a simple directory name")
    work_dir = Path(work_dir).resolve()
    run = work_dir / "outputs" / run_name
    if run.exists():
        raise ValueError("Run already exists; use resume or a new run-name")
    rows = {task: load_prepared(work_dir, spec, task) for task in benchmarks}
    if ids is not None:
        # Keep prepared order; the namespace ("evaluation/<task>") and row id, which
        # seed every case, are independent of which rows are selected.
        wanted, found = set(ids), []
        for task in rows:
            row_ids = [r["id"] for r in rows[task]]
            if len(set(row_ids)) != len(row_ids):
                raise ValueError(f"{task} has duplicated row ids")
            rows[task] = [r for r in rows[task] if r["id"] in wanted]
            found += [r["id"] for r in rows[task]]
        missing = wanted - set(found)
        if missing or len(found) != len(ids):
            raise ValueError("ids missing or ambiguous across benchmarks: " + ", ".join(sorted(missing)))
    else:
        for task in rows:
            rows[task] = rows[task][: len(gpu_ids) if smoke else limit]
    cfg = copy.deepcopy(spec)
    if smoke:
        cfg["experiment"]["max_output_tokens"] = max_output_tokens or 256
        cfg["model"]["rollout_cache_offload_threshold_tokens"] = 0
    elif max_output_tokens is not None:
        cfg["experiment"]["max_output_tokens"] = max_output_tokens
    if gpu_ids == ["cpu"]:
        cfg["model"].update(device="cpu", dtype="float32")
    required_context = (
        cfg["data"]["prompt_limit"]
        + cfg["experiment"]["max_output_tokens"]
        + cfg["experiment"]["memory_capacity_tokens"]
        + cfg["experiment"]["branch_tokens"]
    )
    if required_context > cfg["model"]["max_context_tokens"]:
        raise ValueError("Input/output/memory/branch budgets exceed model.max_context_tokens")
    log_dir = work_dir / "logs" / run_name
    run.mkdir(parents=True)
    log_dir.mkdir(parents=True)
    plan = {
        "created_at": now(),
        "smoke": smoke,
        "benchmarks": benchmarks,
        "arms": arms,
        "source": source_fingerprint(),
        "workers": [],
        "log_dir": str(log_dir),
        "gpus": gpu_ids,
        "seconds_per_arm": hours_per_arm * 3600 if hours_per_arm else None,
        "counts": {task: len(values) for task, values in rows.items()},
        "limit": limit,
        "ids": ids,
        "ids_file": (
            {"path": str(ids_file), "sha256": file_digest(Path(ids_file))} if ids_file else None
        ),
        "monitor": {
            "poll_seconds": 15,
            "initial_detail_seconds": 300,
            "initial_window_seconds": 1800,
            "later_detail_seconds": 3600,
            "checkpoint_stall_seconds": 900,
            "minimum_free_bytes": 2 * 1024**3,
        },
    }
    for arm in arms:
        condition = ARM_CONDITIONS[arm]
        for index, gpu in enumerate(gpu_ids):
            worker_cfg = copy.deepcopy(cfg)
            worker_cfg["experiment"]["arms"] = [condition]
            worker_cfg["execution"]["development_cases_per_task"] = 0
            order = benchmarks[index % len(benchmarks) :] + benchmarks[: index % len(benchmarks)]
            worker_cfg["datasets"] = [{"name": t} for t in order]
            worker_cfg["smoke"] = {"tasks": order, "cases_per_task": 1}
            split = {"tasks": {}}
            for task, values in rows.items():
                selected = values[index :: len(gpu_ids)]
                split["tasks"][task] = {
                    "development": selected if smoke else [],
                    "evaluation": [] if smoke else selected,
                }
            name = f"{arm}-worker{index}"
            atomic_json(run / "configs" / (name + ".json"), worker_cfg)
            atomic_json(run / "configs" / (name + "-split.json"), split)
            plan["workers"].append(
                {
                    "name": name,
                    "arm": arm,
                    "condition": condition,
                    "gpu": gpu,
                    "config": f"configs/{name}.json",
                    "split": f"configs/{name}-split.json",
                }
            )
    for i in range(len(gpu_ids)):
        splits = {
            file_digest(run / plan["workers"][a * len(gpu_ids) + i]["split"])
            for a in range(len(arms))
        }
        assert len(splits) == 1
    atomic_json(run / "plan.json", plan)
    for name, path in source_files().items():
        target = run / "provenance" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    atomic_json(run / "status.json", {"state": "prepared", "at": now()})
    report(run)
    return run


def worker(run, name, probe=False):
    plan = read_json(run / "plan.json")
    if source_fingerprint() != plan["source"]:
        raise ValueError("Frozen source changed; resume rejected")
    assignment = next(w for w in plan["workers"] if w["name"] == name)
    cfg = read_json(run / assignment["config"])
    split = read_json(run / assignment["split"])
    schedule = read_json(run / "schedule.json")[assignment["arm"]]
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = cfg["model"]["cuda_allocator_config"]
    from .backend import LocalModel
    from .cosine import CosineEncoder
    from .long_context import install
    from .recurrent_memory import run_case

    install()
    path = run / "workers" / name
    path.parent.mkdir(exist_ok=True)
    identity = {
        "spec": cfg,
        "source": plan["source"],
        "environment": environment(),
        "assignment": assignment,
        "split_sha256": digest(split),
        "plan_sha256": digest(plan),
        "schedule": schedule,
        "mode": "smoke" if plan["smoke"] else "study",
    }
    with (path.parent / (name + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        store = CheckpointStore(
            path, identity, resume=path.exists(), deadline=schedule["deadline_epoch"], probe=probe
        )
        atomic_json(path / "resolved-config.json", cfg)
        atomic_json(path / "split.json", split)
        for relative in plan["source"]:
            dest = path / "provenance" / relative
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(run / "provenance" / relative, dest)
            if file_digest(dest) != plan["source"][relative]:
                raise ValueError("Changed provenance")
        install_interrupt_handlers()

        def log(message):
            print(now(), message, flush=True)

        try:
            with heartbeat("loading generator", log):
                model = LocalModel(cfg["model"], log)
            if assignment["condition"] == "filtered_futures":
                with heartbeat("loading embedding model", log):
                    model.semantic_encoder = CosineEncoder(cfg["similarity"]["encoder"])
            rows = planned_rows(cfg, split, identity["mode"])
            for namespace, row in rows:
                model._check(
                    [0] * row["prompt_tokens"],
                    cfg["experiment"]["max_output_tokens"]
                    + cfg["experiment"]["memory_capacity_tokens"]
                    + cfg["experiment"]["branch_tokens"],
                )
                store.status(
                    "running", task=row["task"], case_id=row["id"], resources=model.resources()
                )

                def fresh():
                    started = time.monotonic()
                    case = run_case(model, store, row, cfg, namespace, log)
                    case.update(seconds=time.monotonic() - started, finished_epoch=time.time())
                    return case

                case = store.call(
                    namespace + "/" + row["id"] + "/complete",
                    {"row": row, "namespace": namespace, "config_sha256": digest(cfg)},
                    fresh,
                )
                atomic_json(path / "cases" / namespace / (row["id"] + ".json"), case)
                result = case["conditions"][assignment["condition"]]
                outcome = {k: case[k] for k in ("seconds", "finished_epoch")}
                outcome.update(
                    id=row["id"],
                    task=row["task"],
                    correct=result["correct"],
                    prediction=result["prediction"],
                    gold=row["gold"],
                    body_tokens=len(result["body_ids"]),
                    events=len(result["events"]),
                    thinking_complete=result["thinking_complete"],
                    arm=assignment["arm"],
                    context_truncated=row.get("context_truncated", False),
                )
                atomic_json(path / "outcomes" / row["task"] / (row["id"] + ".json"), outcome)
                log(f"completed {row['id']}: correct={result['correct']}")
            store.status("complete")
        except ProbePause:
            store.status("probe_interrupted")
            return 21
        except DeadlineReached:
            store.status("budget_exhausted")
            return 0
        except KeyboardInterrupt:
            store.status("interrupted")
            raise
        except Exception as exc:
            store.status("failed", error=repr(exc))
            raise
    return 0


def audit_run(run, partial=None):
    from .audit import audit

    plan = read_json(run / "plan.json")
    partial = plan["seconds_per_arm"] is not None if partial is None else partial
    for w in plan["workers"]:
        path = run / "workers" / w["name"]
        if not (path / "identity.json").exists() and partial:
            print("AUDIT SKIPPED (phase never started)", w["name"], flush=True)
            continue
        result = audit(path, partial=partial)
        atomic_json(path / "audit.json", result)
        print("AUDIT PASSED", w["name"], flush=True)


def supervise(run):
    run = Path(run).resolve()
    plan = read_json(run / "plan.json")
    settings = plan["monitor"]
    with (run / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if source_fingerprint() != plan["source"]:
            raise ValueError("Frozen source changed; cannot resume")
        state = read_json(run / "status.json")
        if state.get("state") == "complete" and state.get("audits_passed"):
            print("Already complete:", run)
            return
        log_dir = Path(plan["log_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)
        controller = (log_dir / "controller.log").open("a", buffering=1)

        def log(message):
            text = f"{now()} {message}"
            print(text, flush=True)
            controller.write(text + "\n")

        install_interrupt_handlers()
        children = {}
        streams = []
        try:
            schedule = read_json(run / "schedule.json", {})
            if not schedule and plan["seconds_per_arm"] is not None:
                epoch = time.time()
                duration = plan["seconds_per_arm"]
                schedule = {
                    arm: {
                        "start_epoch": epoch + i * duration,
                        "deadline_epoch": epoch + (i + 1) * duration,
                    }
                    for i, arm in enumerate(plan_arms(plan))
                }
                atomic_json(run / "schedule.json", schedule)
            for arm in plan_arms(plan):
                if (run / (arm + "-complete.json")).exists():
                    continue
                if arm not in schedule:
                    schedule[arm] = {"start_epoch": time.time(), "deadline_epoch": None}
                    atomic_json(run / "schedule.json", schedule)
                phase = schedule[arm]
                deadline = phase["deadline_epoch"]
                while time.time() < phase["start_epoch"]:
                    time.sleep(min(15, phase["start_epoch"] - time.time()))
                if deadline is not None and time.time() >= deadline:
                    atomic_json(
                        run / (arm + "-complete.json"), {"at": now(), "expired_before_resume": True}
                    )
                    continue
                assignments = [w for w in plan["workers"] if w["arm"] == arm]
                probes = read_json(run / (arm + "-recovery.json"), {})

                def launch(w, probe=False):
                    env = {
                        **os.environ,
                        "OMP_NUM_THREADS": str(read_json(run / w["config"])["model"]["threads"]),
                        "OPENBLAS_NUM_THREADS": "1",
                        "TOKENIZERS_PARALLELISM": "false",
                    }
                    if w["gpu"] != "cpu":
                        env["CUDA_VISIBLE_DEVICES"] = w["gpu"]
                    stream = (log_dir / (w["name"] + ".log")).open("a", buffering=1)
                    streams.append(stream)
                    args = [
                        sys.executable,
                        "-u",
                        "-m",
                        "lost_tokens",
                        "_worker",
                        "--run",
                        str(run),
                        "--worker",
                        w["name"],
                    ]
                    if probe:
                        args.append("--probe")
                    return subprocess.Popen(args, env=env, stdout=stream, stderr=subprocess.STDOUT)

                children = {
                    w["name"]: launch(w, plan["smoke"] and w["name"] not in probes)
                    for w in assignments
                }
                atomic_json(
                    run / "launch.json",
                    {
                        "at": now(),
                        "pid": os.getpid(),
                        "phase": arm,
                        "worker_pids": {n: p.pid for n, p in children.items()},
                    },
                )
                started = time.time()
                next_detail = 0
                while True:
                    health = {}
                    for w in assignments:
                        name = w["name"]
                        process = children[name]
                        code = process.poll()
                        path = run / "workers" / name
                        if code == 21 and plan["smoke"] and name not in probes:
                            probes[name] = {
                                p.name: file_digest(p)
                                for p in (path / "checkpoints").glob("*.json")
                            }
                            atomic_json(run / (arm + "-recovery.json"), probes)
                            children[name] = launch(w)
                            code = None
                        elif code not in (None, 0):
                            raise RuntimeError(f"{name} exited {code}; see {log_dir}")
                        status = read_json(path / "status.json", {})
                        progress = read_json(path / "progress.json", {})
                        age = time.time() - progress.get("epoch", started)
                        if (
                            code is None
                            and status.get("state") == "running"
                            and age > settings["checkpoint_stall_seconds"]
                        ):
                            raise RuntimeError("Checkpoint progress stalled: " + name)
                        health[name] = {
                            "pid": children[name].pid,
                            "exit_code": code,
                            "status": status,
                            "checkpoint_age_seconds": age,
                            "checkpoints": progress,
                        }
                    if (
                        deadline is not None
                        and time.time() > deadline + 120
                        and any(p.poll() is None for p in children.values())
                    ):
                        raise RuntimeError("Workers exceeded deadline cleanup grace")
                    result = report(run)
                    _, _, outcomes = collect(run)
                    if deadline is not None:
                        eta = max(0, deadline - time.time())
                    else:
                        means = {
                            task: sum(
                                r["seconds"] for r in outcomes[arm].values() if r["task"] == task
                            )
                            / max(1, sum(r["task"] == task for r in outcomes[arm].values()))
                            for task in plan["benchmarks"]
                        }
                        eta = max(
                            (
                                sum(
                                    means[row["task"]] or 300
                                    for ns, row in planned_rows(
                                        read_json(run / w["config"]),
                                        read_json(run / w["split"]),
                                        "smoke" if plan["smoke"] else "study",
                                    )
                                    if row["task"] + "/" + row["id"] not in outcomes[arm]
                                )
                                for w in assignments
                            ),
                            default=0,
                        )
                    snapshot = {
                        "at": now(),
                        "epoch": time.time(),
                        "phase": arm,
                        "workers": health,
                        "eta_seconds": eta,
                        "counts": {a: x["all"]["n"] for a, x in result["own"].items()},
                    }
                    if time.time() >= next_detail:
                        snapshot["free_bytes"] = shutil.disk_usage(run).free
                        if snapshot["free_bytes"] < settings["minimum_free_bytes"]:
                            raise RuntimeError("Insufficient free output storage")
                        if shutil.which("nvidia-smi"):
                            snapshot["gpu_csv"] = subprocess.check_output(
                                [
                                    "nvidia-smi",
                                    "--query-gpu=index,memory.used,utilization.gpu",
                                    "--format=csv,noheader",
                                ],
                                text=True,
                                timeout=20,
                            )
                        atomic_json(
                            log_dir / "monitoring" / (str(int(time.time())) + ".json"), snapshot
                        )
                        next_detail = time.time() + (
                            settings["initial_detail_seconds"]
                            if time.time() - started < settings["initial_window_seconds"]
                            else settings["later_detail_seconds"]
                        )
                    atomic_json(run / "health.json", snapshot)
                    atomic_json(
                        run / "status.json",
                        {
                            "at": now(),
                            "state": "evaluation",
                            "phase": arm,
                            "counts": snapshot["counts"],
                            "eta_seconds": eta,
                        },
                    )
                    log(f"{arm}: completed={snapshot['counts']}; ETA={eta / 60:.1f} min")
                    if all(p.poll() == 0 for p in children.values()):
                        break
                    time.sleep(settings["poll_seconds"])
                for w in assignments:
                    for name, sha in probes.get(w["name"], {}).items():
                        if file_digest(run / "workers" / w["name"] / "checkpoints" / name) != sha:
                            raise ValueError("Recovery changed an existing checkpoint")
                atomic_json(run / (arm + "-complete.json"), {"at": now(), "recovery_checked": True})
            atomic_json(run / "status.json", {"at": now(), "state": "auditing"})
            audit_run(run)
            report(run)
            atomic_json(
                run / "status.json", {"at": now(), "state": "complete", "audits_passed": True}
            )
            log("All phases and audits complete")
        except BaseException as exc:
            atomic_json(
                run / "status.json",
                {
                    "at": now(),
                    "state": "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                    "error": repr(exc),
                },
            )
            raise
        finally:
            for process in children.values():
                if process.poll() is None:
                    process.terminate()
            for process in children.values():
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            for stream in streams:
                stream.close()
            controller.close()
