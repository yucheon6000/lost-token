"""Run frozen multi-path consensus studies with audited, resumable members.

Use the project environment. Every path is an ordinary independently persisted
Lost Tokens run; the voter receives predictions only, never reference answers.
"""

import argparse
from datetime import datetime
import fcntl
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
from zoneinfo import ZoneInfo

from lost_tokens.config import load_spec
from lost_tokens.consensus import answer_consensus
from lost_tokens.core import atomic_json, derived_seed, digest, file_digest, source_fingerprint
from lost_tokens.data import load_prepared
from lost_tokens.runtime import environment


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def now():
    return datetime.now().astimezone().isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_pipeline(path):
    cfg = read(path)
    if cfg["protocol"] != "answer-consensus-v1" or type(cfg["base_seed"]) is not int:
        raise ValueError("Unsupported consensus protocol/seed")
    if type(cfg["validation_repeats"]) is not int or cfg["validation_repeats"] < 1:
        raise ValueError("A positive repeat count is required")
    if not cfg["benchmarks"] or len(set(cfg["benchmarks"])) != len(cfg["benchmarks"]):
        raise ValueError("Distinct benchmarks are required")
    names = [m["name"] for m in cfg["members"]]
    if (
        not names
        or len(set(names)) != len(names)
        or any(not re.fullmatch(r"[a-z0-9_-]+", n) for n in names)
    ):
        raise ValueError("Distinct simple member names are required")
    if any(m["arm"] not in ("baseline", "ours") for m in cfg["members"]):
        raise ValueError("Member arms must be baseline or ours")
    expected = {
        "rule": "unweighted_answer_consensus",
        "tie_break": "earliest_frozen_member",
        "math_equivalence": "locked_math_verify",
        "missing_final": "abstain_with_full_question_denominator",
    }
    if cfg["vote"] != expected:
        raise ValueError("Unsupported voter")
    if cfg["seed_schedule"] != "derived_seed(base_seed, protocol, repeat_index, member_name)":
        raise ValueError("Unsupported seed schedule")
    return cfg


def member_seed(cfg, repeat, member):
    return derived_seed(cfg["base_seed"], cfg["protocol"], repeat, member)


def outcomes(job):
    rows = {}
    for path in Path(job["run"]).glob("workers/*/outcomes/*/*.json"):
        row = read(path)
        if row["id"] in rows or row["task"] != job["task"] or row["arm"] != job["arm"]:
            raise ValueError("Duplicate or unexpected completed member case")
        rows[row["id"]] = row
    return rows


def initialize(args):
    study = args.study
    pipeline = load_pipeline(args.config)
    for directory in ("configs", "ids", "votes"):
        (study / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.config, study / "pipeline.json")
    reference = read(args.baseline_ref)
    if reference["sha256"] != digest(reference["payload"]):
        raise ValueError("Corrupt frozen baseline reference")
    source = source_fingerprint()
    for key in ("lost_tokens/core.py", "lost_tokens/math_scoring.py"):
        if reference["payload"]["conditions"]["scoring_and_seed_sources"][key] != source[key]:
            raise ValueError("The baseline must use the same frozen scorer")
    previous = read(args.previous_study)
    comparison, cohort = {}, {}
    for task in pipeline["benchmarks"]:
        path = args.shared / "evaluation/subsets" / pipeline["cohort"] / (task + ".json")
        shutil.copy2(path, study / "ids" / path.name)
        raw = read(path)
        ids = raw["ids"] if isinstance(raw, dict) else raw
        baseline = {r["id"]: r for r in reference["payload"]["outcomes"][task]}
        selected = previous["comparison"][task][previous["selectors"][task]]["cases"]
        if not set(ids) <= baseline.keys() or not set(ids) <= selected.keys():
            raise ValueError("Reference comparison is missing canonical IDs")
        baseline = {i: baseline[i] for i in ids}
        selected = {i: selected[i] for i in ids}
        comparison[task] = {"baseline": baseline, "previous_ours": selected}
        cohort[task] = {"n": len(ids), "ids": ids, "ids_sha256": digest(ids)}
    module_spec = importlib.util.spec_from_file_location(
        "shared_eval", ROOT / "scripts/shared_eval.py"
    )
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    first = pipeline["members"][0]
    first_path = args.config.parent / first["config"]
    manifest = {
        "created_at": now(),
        "execution_branch": git("branch", "--show-current"),
        "code_commit": git("rev-parse", "HEAD"),
        "repo": str(ROOT),
        "source": source,
        "pipeline": pipeline,
        "cohort": cohort,
        "comparison": comparison,
        "baseline_reference_sha256": reference["sha256"],
        "original_baseline_reference_sha256": reference["payload"].get("original_reference_sha256"),
        "baseline_reference_file_sha256": file_digest(args.baseline_ref),
        "work_dir": str(args.work_dir),
        "model_cache": str(args.model_cache),
        "gpus": args.gpus,
        "name": args.name,
        "environment": helper.collect_environment(args.gpus, load_spec(first_path)),
        "uv_lock_sha256": file_digest(ROOT / "uv.lock"),
        "inputs": {},
        "jobs": [],
        "preflight_runs": [str(p) for p in args.preflight_run],
        "branch_rule": "name-YYYY-MM-DD using completion date in Asia/Seoul",
        "cost_scope": "Five full-generation members per question per repeat; frozen single-pass baselines are unchanged. AR members are ensemble components, not replacement benchmark baselines.",
    }
    for repeat in range(pipeline["validation_repeats"]):
        for task in pipeline["benchmarks"]:
            for index, member in enumerate(pipeline["members"]):
                name = member["config"] if "config" in member else member["config_by_task"][task]
                original = args.config.parent / name
                cfg = load_spec(original)
                cfg["experiment"]["seed"] = member_seed(pipeline, repeat, member["name"])
                rows = load_prepared(args.work_dir, cfg, task)
                if {r["id"] for r in rows} != set(cohort[task]["ids"]):
                    raise ValueError(
                        "This accuracy study requires the entire task, without redraws"
                    )
                path = study / "configs" / f"r{repeat}-{task}-{member['name']}.json"
                atomic_json(path, cfg)
                run_name = f"{study.name}-r{repeat}-{task}-{member['name']}"
                manifest["jobs"].append(
                    {
                        "repeat": repeat,
                        "task": task,
                        "member": member["name"],
                        "member_index": index,
                        "arm": member["arm"],
                        "config": str(path),
                        "config_sha256": file_digest(path),
                        "seed": cfg["experiment"]["seed"],
                        "n_required": len(rows),
                        "ids_file": str(study / "ids" / (task + ".json")),
                        "run": str(args.work_dir / "outputs" / run_name),
                    }
                )
    for path in [
        *(study / "configs").glob("*.json"),
        *(study / "ids").glob("*.json"),
        study / "pipeline.json",
    ]:
        manifest["inputs"][str(path)] = file_digest(path)
    atomic_json(study / "environment.json", manifest["environment"])
    atomic_json(study / "manifest.json", manifest)
    atomic_json(study / "manifest-sha256.json", {"sha256": file_digest(study / "manifest.json")})
    state = {
        "state": "prepared",
        "started_at": None,
        "jobs": [dict(j, state="queued") for j in manifest["jobs"]],
        "ensembles": {},
    }
    export(study, manifest, state)
    return manifest, state


def check_inputs(args, manifest):
    if (
        file_digest(args.study / "manifest.json")
        != read(args.study / "manifest-sha256.json")["sha256"]
    ):
        raise ValueError("Immutable study manifest changed")
    if (
        source_fingerprint() != manifest["source"]
        or git("rev-parse", "HEAD") != manifest["code_commit"]
    ):
        raise ValueError("Execution source or commit changed")
    if (
        environment() != manifest["environment"]["runtime"]
        or file_digest(ROOT / "uv.lock") != manifest["uv_lock_sha256"]
    ):
        raise ValueError("Runtime changed")
    for path, sha in manifest["inputs"].items():
        if file_digest(Path(path)) != sha:
            raise ValueError(f"Frozen input changed: {path}")


def finish_member(job, manifest):
    run = Path(job["run"])
    status, plan = read(run / "status.json"), read(run / "plan.json")
    if status["state"] != "complete" or not status.get("audits_passed"):
        raise ValueError("Member did not finish with passing audits")
    if (
        plan["source"] != manifest["source"]
        or plan["arms"] != [job["arm"]]
        or plan["seconds_per_arm"] is not None
    ):
        raise ValueError("Member protocol/provenance mismatch")
    rows = outcomes(job)
    if set(rows) != set(manifest["cohort"][job["task"]]["ids"]):
        raise ValueError("Member full-cohort coverage differs")
    schedule = read(run / "schedule.json")[job["arm"]]
    end = datetime.fromisoformat(read(run / f"{job['arm']}-complete.json")["at"]).timestamp()
    return {
        "state": "complete",
        "n": len(rows),
        "correct": sum(r["correct"] for r in rows.values()),
        "missing": sum(r["prediction"] is None for r in rows.values()),
        "audits_passed": True,
        "body_tokens": sum(r["body_tokens"] for r in rows.values()),
        "phase_wall_seconds": end - schedule["start_epoch"],
        "finished_at": now(),
        "outcomes_sha256": digest([rows[i] for i in sorted(rows)]),
    }


def finish_vote(study, manifest, jobs, key):
    jobs = sorted(jobs, key=lambda job: (job["repeat"], job["member_index"]))
    task = jobs[0]["task"]
    banks = [outcomes(job) for job in jobs]
    comparison = manifest["comparison"][task]
    ids = manifest["cohort"][task]["ids"]
    case_results = []
    for ident in ids:
        samples = [bank[ident] for bank in banks]
        # Selection has no access to correctness, gold, or reference metadata.
        vote = answer_consensus(
            [r["prediction"] for r in samples], "choice" if task == "gpqa" else "math", "ABCD"
        )
        selected = vote["selected_member"]
        correct = bool(samples[selected]["correct"]) if selected is not None else False
        case_results.append(
            {
                "id": ident,
                "task": task,
                "vote": vote,
                "correct": correct,
                "member_predictions": [r["prediction"] for r in samples],
                "member_runs": [Path(j["run"]).name for j in jobs],
            }
        )
    result = {
        "task": task,
        "members_per_question": len(jobs),
        "n": len(ids),
        "correct": sum(r["correct"] for r in case_results),
        "missing": sum(r["vote"]["prediction"] is None for r in case_results),
        "strict_majority_cases": sum(r["vote"]["strict_majority"] for r in case_results),
        "ties": sum(r["vote"]["tied"] for r in case_results),
        "body_tokens": sum(j["body_tokens"] for j in jobs),
        "sum_member_phase_wall_seconds": sum(j["phase_wall_seconds"] for j in jobs),
        "input_outcome_hashes": [j["outcomes_sha256"] for j in jobs],
    }
    for name, reference in comparison.items():
        result[name + "_correct"] = sum(reference[i]["correct"] for i in ids)
        result["wins_" + name] = sum(
            r["correct"] and not reference[r["id"]]["correct"] for r in case_results
        )
        result["losses_" + name] = sum(
            reference[r["id"]]["correct"] and not r["correct"] for r in case_results
        )
    result["beats_both"] = result["correct"] > max(
        result["baseline_correct"], result["previous_ours_correct"]
    )
    atomic_json(study / "votes" / f"{key}.json", {"summary": result, "cases": case_results})
    return result


def update_votes(study, manifest, state):
    pipeline = manifest["pipeline"]
    for repeat in range(pipeline["validation_repeats"]):
        for task in pipeline["benchmarks"]:
            key = f"r{repeat}-{task}"
            jobs = [j for j in state["jobs"] if j["repeat"] == repeat and j["task"] == task]
            if key not in state["ensembles"] and all(j["state"] == "complete" for j in jobs):
                state["ensembles"][key] = finish_vote(study, manifest, jobs, key)
    if pipeline.get("report_pooled_consensus"):
        for task in pipeline["benchmarks"]:
            key = "pooled-" + task
            jobs = [j for j in state["jobs"] if j["task"] == task]
            if key not in state["ensembles"] and all(j["state"] == "complete" for j in jobs):
                state["ensembles"][key] = finish_vote(study, manifest, jobs, key)


def export(study, manifest, state):
    lines = [
        "# Fixed-roster consensus validation",
        "",
        f"Updated {now()}; state={state['state']}",
        "",
        "Fresh per-member seeds. Full AIME/HMMT/GPQA canonical IDs, two repeats. Five full generations per question per repeat; pooled result uses ten. This is increased-compute accuracy, not equal-compute superiority.",
        "",
        "| Group | Dataset | n | Frozen AR | Previous ours | Consensus | Beats both |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for key, value in state["ensembles"].items():
        n = value["n"]
        cells = [
            f"{value[k]}/{n} ({100 * value[k] / n:.2f}%)"
            for k in ("baseline_correct", "previous_ours_correct", "correct")
        ]
        lines.append(
            f"| {key.split('-')[0]} | {value['task']} | {n} | "
            + " | ".join(cells)
            + f" | {value['beats_both']} |"
        )
    lines += [
        "",
        "| Repeat | Dataset | Member | Completed / full n | Correct | State |",
        "|---|---|---|---:|---:|---|",
    ]
    for job in state["jobs"]:
        lines.append(
            f"| {job['repeat']} | {job['task']} | {job['member']} | {job.get('n', 0)}/{job['n_required']} | {job.get('correct', 0)} | {job['state']} |"
        )
    lines += [
        "",
        "The cached mixed-roster result was exploratory, not this fresh-seed validation. No parameter or roster changes are made after seeing new results. A repeated-set win is not a guarantee on unseen data. Code branch follows the actual completion date in Asia/Seoul.",
    ]
    (study / "results.md").write_text("\n".join(lines) + "\n")
    atomic_json(study / "status.json", state)


def wait_preflight(manifest):
    for path in manifest["preflight_runs"]:
        run = Path(path)
        if not (run / "status.json").exists():
            return False
        status = read(run / "status.json")
        if status["state"] in ("failed", "interrupted"):
            raise ValueError("GPU preflight failed")
        if status["state"] != "complete":
            return False
        if not status.get("audits_passed"):
            raise ValueError("GPU preflight audit failed")
        rows = [read(p) for p in run.glob("workers/*/outcomes/*/*.json")]
        if len(rows) != 2 or any(r["prediction"] is None for r in rows):
            raise ValueError("GPU preflight did not yield scored final responses")
    return True


def gpus_available(gpus):
    raw = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits"], text=True
    )
    used = {i.strip(): int(m.strip()) for i, m in (row.split(",") for row in raw.splitlines())}
    return all(used[g] < 128 for g in gpus.split(","))


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
    ):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--config", type=Path, default=ROOT / "configs/consensus5.json")
    p.add_argument("--preflight-run", type=Path, action="append", default=[])
    p.add_argument("--gpus", required=True)
    p.add_argument("--name", required=True)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    args.preflight_run = [p.expanduser().absolute() for p in args.preflight_run]
    args.study.mkdir(parents=True, exist_ok=True)
    with (args.study / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (args.study / "manifest.json").exists():
            manifest, state = read(args.study / "manifest.json"), read(args.study / "status.json")
            if manifest["gpus"] != args.gpus or manifest["work_dir"] != str(args.work_dir):
                raise ValueError("Resume allocation/storage changed")
        else:
            manifest, state = initialize(args)
        if args.action == "report":
            update_votes(args.study, manifest, state)
            export(args.study, manifest, state)
            return
        check_inputs(args, manifest)
        if args.action == "prepare":
            print("Prepared", args.study, "member runs", len(state["jobs"]), flush=True)
            return
        current = None
        try:
            while not wait_preflight(manifest):
                state["state"] = "waiting_for_preflights"
                export(args.study, manifest, state)
                time.sleep(30)
            for job in state["jobs"]:
                current = job
                if job["state"] == "complete":
                    job.update(finish_member(job, manifest))
                    continue
                check_inputs(args, manifest)
                while not gpus_available(args.gpus):
                    state["state"] = "waiting_for_gpus"
                    export(args.study, manifest, state)
                    time.sleep(30)
                state["started_at"] = state["started_at"] or now()
                state["state"] = "running"
                job.update(state="running", started_at=now())
                export(args.study, manifest, state)
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
                        job["arm"],
                        "--gpus",
                        args.gpus,
                        "--run-name",
                        run.name,
                        "--ids-file",
                        job["ids_file"],
                    ]
                job.setdefault("commands", []).append(cmd)
                print(
                    "START",
                    job["repeat"],
                    job["task"],
                    job["member"],
                    job["n_required"],
                    flush=True,
                )
                with (args.study / f"r{job['repeat']}-{job['task']}-{job['member']}.log").open(
                    "a"
                ) as log:
                    process = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                    while True:
                        try:
                            code = process.wait(timeout=60)
                            break
                        except subprocess.TimeoutExpired:
                            rows = outcomes(job)
                            job.update(
                                n=len(rows), correct=sum(r["correct"] for r in rows.values())
                            )
                            export(args.study, manifest, state)
                            print(
                                "PROGRESS",
                                job["repeat"],
                                job["task"],
                                job["member"],
                                len(rows),
                                "/",
                                job["n_required"],
                                flush=True,
                            )
                if code:
                    raise RuntimeError(
                        f"Member failed: {job['repeat']} {job['task']} {job['member']} ({code})"
                    )
                job.update(finish_member(job, manifest))
                update_votes(args.study, manifest, state)
                export(args.study, manifest, state)
                print(
                    "COMPLETE",
                    job["repeat"],
                    job["task"],
                    job["member"],
                    job["correct"],
                    "/",
                    job["n"],
                    flush=True,
                )
            branch = f"{args.name}-{datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()}"
            if git("branch", "--show-current") != branch:
                subprocess.run(["git", "branch", "-m", branch], cwd=ROOT, check=True)
            state.update(state="complete", finished_at=now(), result_branch=branch)
            update_votes(args.study, manifest, state)
            export(args.study, manifest, state)
        except BaseException:
            state.update(state="failed", error=traceback.format_exc())
            if current and current["state"] != "complete":
                current["state"] = "failed"
            export(args.study, manifest, state)
            raise


if __name__ == "__main__":
    main()
