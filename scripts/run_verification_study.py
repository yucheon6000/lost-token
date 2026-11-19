"""Freeze and run single-answer local-verification/control comparisons.

Each question produces one continuing solution per experimental condition. The
conditions are evaluated separately and never combined, selected or voted on.
"""

import argparse
from datetime import datetime
import fcntl
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from zoneinfo import ZoneInfo

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json, atomic_text, digest, file_digest, source_fingerprint
from lost_tokens.data import load_prepared
from lost_tokens.runtime import environment, install_interrupt_handlers


ROOT = Path(__file__).resolve().parents[1]
helper_spec = importlib.util.spec_from_file_location(
    "shared_helpers", ROOT / "scripts/shared_eval.py"
)
shared = importlib.util.module_from_spec(helper_spec)
helper_spec.loader.exec_module(shared)


def read(path):
    return json.loads(Path(path).read_text())


def now():
    return datetime.now().astimezone().isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def rows(job):
    found = {}
    for path in Path(job["run"]).glob("workers/*/outcomes/*/*.json"):
        row = read(path)
        if row["id"] in found or row["task"] != job["task"] or row["arm"] != "ours":
            raise ValueError("Unexpected or duplicate outcome")
        found[row["id"]] = row
    return found


def validate_pair(control, verify):
    base, treatment = load_spec(control), load_spec(verify)
    policy = treatment["experiment"].pop("disagreement_verification", None)
    control_policy = base["experiment"].pop("disagreement_verification", None)
    if control_policy is not None or policy is None or base != treatment:
        raise ValueError("Control/treatment must differ only in the verification policy")


def frozen_cohort(work, config, task, shared_root, full_manifest=None):
    """Use committed IDs verbatim; a full cohort is never a redrawn subset."""
    shared.verify_cohort(work, config, [task], shared_root / "evaluation/subsets/shared-v1")
    if full_manifest is None:
        path = shared_root / "evaluation/subsets/shared-v1" / (task + ".json")
        return read(path)["ids"], path, file_digest(path.parent / "manifest.json"), "shared-v1"
    manifest = read(full_manifest)
    if manifest["version"] != "full-v1":
        raise ValueError("Expected the committed full-v1 cohort")
    source = source_fingerprint()
    for key in ("lost_tokens/data.py", "lost_tokens/datasets.json"):
        if source[key] != manifest["source"][key]:
            raise ValueError("Dataset adapter/pins differ from the committed full cohort")
    entry = manifest["datasets"][task]
    ids = entry["ids"]
    prepared = load_prepared(work, config, task)
    by_id = {r["id"]: r for r in prepared}
    if (
        len(ids) != len(set(ids))
        or len(ids) != entry["n"]
        or len(ids) != entry["full_n"]
        or len(prepared) != len(by_id)
        or set(ids) != set(by_id)
        or digest(ids) != entry["ids_sha256"]
        or digest([by_id[i] for i in ids]) != entry["rows_sha256"]
    ):
        raise ValueError("Committed full cohort IDs/rows/coverage differ: " + task)
    return ids, full_manifest, file_digest(full_manifest), manifest["version"]


def reuse_completed(study, jobs, cohort, source, gpus):
    """Reuse audited identical conditions, preserving original timing and provenance."""
    parent, previous = read(study / "manifest.json"), read(study / "status.json")
    if previous["state"] != "complete" or parent["source"] != source or parent["gpus"] != gpus:
        raise ValueError("Reusable study is incomplete or has different generation/allocation")
    old = {(j["task"], j["variant"]): j for j in previous["jobs"]}
    inputs = {
        str(study / name): file_digest(study / name) for name in ("manifest.json", "status.json")
    }
    for job in jobs:
        original = old.get((job["task"], job["variant"]))
        if original is None:
            continue
        if original["state"] != "complete" or not original.get("audits_passed"):
            raise ValueError("Reusable condition is not audited")
        if load_spec(original["config"]) != load_spec(job["config"]):
            raise ValueError("Reusable condition settings differ")
        run = Path(original["run"])
        status, plan = read(run / "status.json"), read(run / "plan.json")
        found = rows(original)
        if (
            status.get("audits_passed") is not True
            or status["state"] != "complete"
            or plan["source"] != source
            or plan["arms"] != ["ours"]
            or plan["seconds_per_arm"] is not None
            or plan["gpus"] != gpus.split(",")
            or set(found) != set(cohort[job["task"]]["ids"])
            or digest([found[i] for i in sorted(found)]) != original["outcomes_sha256"]
        ):
            raise ValueError("Reusable condition identity/coverage/outcomes differ")
        inputs[str(Path(original["config"]))] = file_digest(Path(original["config"]))
        for name in ("status.json", "plan.json", "schedule.json"):
            inputs[str(run / name)] = file_digest(run / name)
        original_metrics = {k: v for k, v in original.items() if k not in ("config", "ids_file")}
        job.update(original_metrics)
        job["reused_from"] = {
            "study": str(study),
            "code_commit": parent["code_commit"],
            "finished_at": original["finished_at"],
            "timing": "original execution; no new GPU generation",
        }
    return inputs


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
        raise ValueError("Commit the execution source, settings and tests before freezing")
    pipeline = read(args.pipeline)
    if pipeline["protocol"] != "single-stream-local-verification-v1":
        raise ValueError("Unsupported study protocol")
    if sorted(pipeline["condition_order"]) != ["control", "verification"]:
        raise ValueError("Exactly the separate control and verification conditions are required")
    required = pipeline.get("required_benchmarks")
    if required and (
        set(pipeline["benchmarks"]) != set(required) or len(pipeline["benchmarks"]) != len(required)
    ):
        raise ValueError("The required whole benchmark suite must not be truncated")
    if pipeline.get("cohort") == "full-v1" and args.cohort_manifest is None:
        raise ValueError("The whole-suite protocol requires the committed full-v1 manifest")
    baseline, previous = read(args.baseline_ref), read(args.previous_study)
    if baseline["sha256"] != digest(baseline["payload"]):
        raise ValueError("Corrupt frozen baseline")
    source = source_fingerprint()
    for key in ("lost_tokens/core.py", "lost_tokens/math_scoring.py"):
        if baseline["payload"]["conditions"]["scoring_and_seed_sources"][key] != source[key]:
            raise ValueError("Scoring or seed code differs from the baseline")
    args.study.mkdir(parents=True, exist_ok=True)
    for name in ("configs", "ids", "comparison"):
        (args.study / name).mkdir(exist_ok=True)
    inputs = {str(args.pipeline): file_digest(args.pipeline)}
    for source_path, name in [
        (args.baseline_ref, "baseline-reference.json"),
        (args.previous_study, "previous-study.json"),
    ]:
        target = args.study / "comparison" / name
        shutil.copy2(source_path, target)
        inputs[str(target)] = file_digest(target)
    cohort, comparison = {}, {}
    jobs = []
    for task in pipeline["benchmarks"]:
        configs = pipeline["configs_by_task"][task]
        validate_pair(ROOT / configs["control"], ROOT / configs["verification"])
        config = load_spec(ROOT / configs["control"])
        ids, ids_path, cohort_sha, cohort_version = frozen_cohort(
            args.work_dir, config, task, args.shared, args.cohort_manifest
        )
        id_copy = args.study / "ids" / (task + ".json")
        atomic_json(id_copy, {"ids": ids})
        inputs[str(ids_path)] = file_digest(ids_path)
        cohort[task] = {
            "ids": ids,
            "n": len(ids),
            "manifest_sha256": cohort_sha,
            "version": cohort_version,
        }
        baselines = {r["id"]: r for r in baseline["payload"]["outcomes"][task]}
        old = previous["comparison"][task][pipeline["previous_selectors"][task]]["cases"]
        if not set(ids) <= baselines.keys() or not set(ids) <= old.keys():
            raise ValueError("Comparison does not cover the fixed cohort")
        comparison[task] = {
            "baseline": {i: baselines[i] for i in ids},
            "previous_ours": {i: old[i] for i in ids},
        }
        conditions = baseline["payload"]["conditions"]
        if any(
            config["experiment"][k] != conditions["decoding"][k]
            for k in ("seed", "temperature", "top_p", "top_k", "max_output_tokens")
        ):
            raise ValueError("Sampling/seed/output budget differs from frozen AR")
        if any(config["model"][k] != v for k, v in conditions["model"].items()):
            raise ValueError("Model/backend differs from frozen AR")
        for variant in pipeline["condition_order"]:
            source_path = ROOT / configs[variant]
            dest = args.study / "configs" / f"{task}-{variant}.json"
            shutil.copy2(source_path, dest)
            inputs[str(source_path)] = file_digest(source_path)
            inputs[str(dest)] = file_digest(dest)
            inputs[str(id_copy)] = file_digest(id_copy)
            jobs.append(
                {
                    "task": task,
                    "variant": variant,
                    "arm": "ours",
                    "state": "queued",
                    "n_required": len(ids),
                    "config": str(dest),
                    "ids_file": str(id_copy),
                    "run": str(args.work_dir / "outputs" / f"{args.study.name}-{task}-{variant}"),
                }
            )
    if args.reuse_study:
        inputs.update(reuse_completed(args.reuse_study, jobs, cohort, source, args.gpus))
    for path in (Path(__file__), ROOT / "scripts/shared_eval.py", ROOT / "uv.lock"):
        inputs[str(path)] = file_digest(path)
    env = shared.collect_environment(
        args.gpus, load_spec(args.study / "configs" / f"{pipeline['benchmarks'][0]}-control.json")
    )
    manifest = {
        "pipeline": pipeline,
        "source": source,
        "code_commit": git("rev-parse", "HEAD"),
        "execution_branch": git("branch", "--show-current"),
        "shared_commit": git("-C", str(args.shared), "rev-parse", "HEAD"),
        "inputs": inputs,
        "cohort": cohort,
        "comparison": comparison,
        "environment": env,
        "gpus": args.gpus,
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "preflight_run": str(args.preflight_run),
        "cohort_manifest": str(args.cohort_manifest) if args.cohort_manifest else None,
        "reuse_study": str(args.reuse_study) if args.reuse_study else None,
        "name": args.name,
    }
    atomic_json(args.study / "manifest.json", manifest)
    atomic_json(args.study / "manifest-sha256.json", {"sha256": digest(manifest)})
    atomic_json(args.study / "environment.json", env)
    atomic_json(args.study / "pipeline.json", pipeline)
    return manifest, {"state": "prepared", "started_at": None, "jobs": jobs}


def check_inputs(args, manifest):
    if digest(manifest) != read(args.study / "manifest-sha256.json")["sha256"]:
        raise ValueError("Study manifest changed")
    if (
        source_fingerprint() != manifest["source"]
        or git("rev-parse", "HEAD") != manifest["code_commit"]
    ):
        raise ValueError("Frozen execution source changed")
    for key, value in {
        "gpus": args.gpus,
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "preflight_run": str(args.preflight_run),
        "cohort_manifest": str(args.cohort_manifest) if args.cohort_manifest else None,
        "reuse_study": str(args.reuse_study) if args.reuse_study else None,
        "name": args.name,
    }.items():
        if manifest[key] != value:
            raise ValueError("Resume allocation/storage/preflight identity differs: " + key)
    if environment() != manifest["environment"]["runtime"]:
        raise ValueError("Frozen runtime changed")
    for path, sha in manifest["inputs"].items():
        if file_digest(Path(path)) != sha:
            raise ValueError("Frozen input changed: " + path)


def export(study, manifest, state):
    lines = [
        "# Single-stream disagreement verification",
        "",
        f"Updated {now()}; state={state['state']}",
        "",
        "Each condition generates one solution per question. No completed-answer voting, reranking or best-of-N selection. Verification consumes the same 32K body cap; short speculative candidates and side-input costs are reported separately.",
        "",
        "| Dataset | Condition | Completed / full | Correct | Accuracy | Frozen AR on same completed IDs | Wins/losses vs AR | State | Origin |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for job in state["jobs"]:
        found = rows(job)
        ids = set(found)
        if not ids <= set(manifest["cohort"][job["task"]]["ids"]):
            raise ValueError("Outcome is outside the canonical cohort")
        reference = manifest["comparison"][job["task"]]["baseline"]
        n, correct = len(ids), sum(r["correct"] for r in found.values())
        bc = sum(reference[i]["correct"] for i in ids)
        wins = sum(bool(found[i]["correct"]) and not reference[i]["correct"] for i in ids)
        losses = sum(bool(reference[i]["correct"]) and not found[i]["correct"] for i in ids)
        job.update(
            n=n,
            correct=correct,
            baseline_correct_on_completed=bc,
            wins_baseline=wins,
            losses_baseline=losses,
        )
        accuracy = f"{100 * correct / n:.2f}%" if n else "—"
        origin = "reused audited result" if job.get("reused_from") else "new generation"
        lines.append(
            f"| {job['task']} | {job['variant']} | {n}/{job['n_required']} | {correct} | {accuracy} | {bc}/{n} | {wins}/{losses} | {job['state']} | {origin} |"
        )
    lines += ["", "Full frozen baseline:"]
    for task, group in manifest["comparison"].items():
        c = sum(r["correct"] for r in group["baseline"].values())
        lines.append(f"- {task}: {c}/{len(group['baseline'])}")
    lines += [
        "",
        "Control and treatment use identical settings and per-position seeds; only the bounded verification task differs. GPU batching can still introduce numerical variability. Both conditions and all failures are retained. Branch dates follow actual completion in Asia/Seoul.",
    ]
    atomic_json(study / "status.json", state)
    atomic_text(study / "results.md", "\n".join(lines) + "\n")


def finish(job, manifest):
    run = Path(job["run"])
    status, plan = read(run / "status.json"), read(run / "plan.json")
    if status["state"] != "complete" or status.get("audits_passed") is not True:
        raise ValueError("Condition did not complete with passing audits")
    if (
        plan["source"] != manifest["source"]
        or plan["arms"] != ["ours"]
        or plan["seconds_per_arm"] is not None
    ):
        raise ValueError("Condition provenance/budget differs")
    found = rows(job)
    if set(found) != set(manifest["cohort"][job["task"]]["ids"]):
        raise ValueError("Condition did not cover every fixed ID")
    checks = check_tokens = checked_cases = 0
    cost = {}
    for path in run.glob("workers/*/cases/evaluation/*/*.json"):
        case = read(path)["conditions"]["filtered_futures"]
        local = [e["verification"] for e in case["events"] if e.get("verification")]
        checked_cases += bool(local)
        checks += len(local)
        check_tokens += sum(len(v["body_ids"]) for v in local)
        for key, value in case["policy_cost"].items():
            cost[key] = cost.get(key, 0) + value
    schedule = read(run / "schedule.json")["ours"]
    end = datetime.fromisoformat(read(run / "ours-complete.json")["at"]).timestamp()
    return {
        "state": "complete",
        "finished_at": status["at"],
        "audits_passed": True,
        "verification_checks": checks,
        "verification_body_tokens": check_tokens,
        "checked_cases": checked_cases,
        "body_tokens": sum(r["body_tokens"] for r in found.values()),
        "policy_cost": cost,
        "phase_wall_seconds": end - schedule["start_epoch"],
        "outcomes_sha256": digest([found[i] for i in sorted(found)]),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("prepare", "run", "report"))
    for name in (
        "study",
        "work-dir",
        "model-cache",
        "shared",
        "baseline-ref",
        "previous-study",
        "uv",
        "pipeline",
        "preflight-run",
    ):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--gpus", required=True)
    p.add_argument("--name", required=True)
    p.add_argument(
        "--cohort-manifest",
        type=Path,
        help="Committed full-v1 manifest; use every prepared row without redrawing IDs",
    )
    p.add_argument(
        "--reuse-study",
        type=Path,
        help="Audited prior identical conditions; preserve their original results/provenance",
    )
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    args.study.mkdir(parents=True, exist_ok=True)
    install_interrupt_handlers()
    with (args.study / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (args.study / "manifest.json").exists():
            manifest, state = read(args.study / "manifest.json"), read(args.study / "status.json")
        else:
            manifest, state = initialize(args)
        check_inputs(args, manifest)
        if args.action in ("prepare", "report") or state["state"] == "complete":
            export(args.study, manifest, state)
            return
        proof = read(args.preflight_run / "status.json")
        preflight = read(args.preflight_run / "preflight-proof.json")
        if (
            proof.get("audits_passed") is not True
            or read(args.preflight_run / "plan.json")["source"] != manifest["source"]
            or preflight["source"] != manifest["source"]
            or preflight["completed"] != preflight["required"]
            or preflight["extracted_finals"] < preflight["required"] * 0.9
            or preflight["verification_checks"] < 1
        ):
            raise ValueError("Matching audited GPU preflight required")
        process = None
        current = None
        try:
            for job in state["jobs"]:
                current = job
                if job["state"] == "complete":
                    continue
                check_inputs(args, manifest)
                shared.require_free_gpus(args.gpus)
                state.update(state="running", started_at=state["started_at"] or now())
                job.update(state="running", started_at=job.get("started_at") or now())
                run = Path(job["run"])
                cmd = [str(args.uv), "run", "--frozen", "python", "-u", "-m", "lost_tokens"]
                if run.exists():
                    cmd += ["resume", "--run", str(run)]
                else:
                    cmd += [
                        "run",
                        "--config",
                        job["config"],
                        "--work-dir",
                        str(args.work_dir),
                        "--model-cache",
                        str(args.model_cache),
                        "--benchmarks",
                        job["task"],
                        "--arms",
                        "ours",
                        "--gpus",
                        args.gpus,
                        "--run-name",
                        run.name,
                        "--ids-file",
                        job["ids_file"],
                    ]
                job.setdefault("commands", []).append(cmd)
                export(args.study, manifest, state)
                print("START", job["task"], job["variant"], now(), flush=True)
                with (args.study / f"{job['task']}-{job['variant']}.log").open("a") as log:
                    process = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                    while process.poll() is None:
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            export(args.study, manifest, state)
                            print(
                                "PROGRESS",
                                job["task"],
                                job["variant"],
                                job["n"],
                                "/",
                                job["n_required"],
                                flush=True,
                            )
                if process.returncode:
                    raise RuntimeError(
                        "Condition failed; resume preserves its original schedule: " + job["run"]
                    )
                job.update(finish(job, manifest))
                export(args.study, manifest, state)
                print(
                    "COMPLETE",
                    job["task"],
                    job["variant"],
                    job["correct"],
                    "/",
                    job["n"],
                    flush=True,
                )
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
            if process is not None and process.poll() is None:
                process.send_signal(2)
                try:
                    process.wait(timeout=45)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=45)
            export(args.study, manifest, state)


if __name__ == "__main__":
    main()
