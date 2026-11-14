"""Prepare, verify, run/resume and document the fixed shared baseline/ours study."""

import argparse
import csv
from datetime import datetime
import json
import importlib.metadata
import os
import platform
from pathlib import Path
import re
import subprocess
import sys

from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.core import atomic_json, digest, file_digest, source_fingerprint
from lost_tokens.data import download_datasets, download_models, load_prepared, prepare, sources


REPO = Path(__file__).resolve().parents[1]
SHARED_ROOT = REPO / ".shared-evaluation"
COHORT = SHARED_ROOT / "evaluation/subsets/shared-v1"


def verify_cohort(work, spec, tasks, cohort=COHORT):
    manifest = json.loads((cohort / "manifest.json").read_text())
    if spec["data"] != manifest["data"]:
        raise ValueError("Data/prompt settings differ from the frozen cohort")
    if any(spec["model"][k] != v for k, v in manifest["model"].items()):
        raise ValueError("Generator/tokenizer revision differs from the frozen cohort")
    if file_digest(REPO / "src/lost_tokens/data.py") != manifest["data_adapter_sha256"]:
        raise ValueError("Data adapter differs; a new cohort version is required")
    for task in tasks:
        entry = manifest["datasets"][task]
        path = cohort / entry["ids_file"]
        ids = json.loads(path.read_text())["ids"]
        if file_digest(path) != entry["ids_file_sha256"] or digest(ids) != entry["ids_sha256"]:
            raise ValueError(f"Frozen ID file changed: {task}")
        rows = load_prepared(work, spec, task)
        wanted = set(ids)
        selected = sorted((r for r in rows if r["id"] in wanted), key=lambda r: r["id"])
        if (
            len(rows) != entry["full_n"]
            or len(ids) != len(set(ids))
            or len(selected) != entry["n"]
            or digest(selected) != entry["selected_rows_sha256"]
            or digest(sources()[task]) != entry["source_definition_sha256"]
        ):
            raise ValueError(f"Dataset identity or selected rows differ: {task}")
    return manifest


def require_free_gpus(gpus):
    from lost_tokens.runner import devices

    selected = set(devices(gpus))
    gpu_rows = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,uuid", "--format=csv,noheader"], text=True
    )
    uuids = {
        line.split(",")[1].strip()
        for line in gpu_rows.splitlines()
        if line.split(",")[0].strip() in selected
    }
    processes = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=gpu_uuid,pid", "--format=csv,noheader"], text=True
    )
    busy = [
        line
        for line in processes.splitlines()
        if line.split(",")[0].strip() in uuids and line.split(",")[1].strip() != str(os.getpid())
    ]
    if busy:
        raise RuntimeError(
            "Selected GPUs already have compute processes; do not kill them: " + str(busy)
        )


def collect_environment(gpus, spec):
    from lost_tokens.runner import devices
    from lost_tokens.runtime import environment

    selected = devices(gpus)
    raw = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ],
        text=True,
    )
    inventory = []
    for row in csv.reader(raw.splitlines()):
        index, name, uuid, memory, driver = [value.strip() for value in row]
        if index in selected:
            inventory.append(
                {
                    "physical_index": index,
                    "name": name,
                    "uuid": uuid,
                    "memory_total_mib": int(memory),
                    "driver_version": driver,
                }
            )
    if len(inventory) != len(selected):
        raise ValueError("GPU inventory does not match selected device count")
    return {
        "recorded_at": datetime.now().astimezone().isoformat(),
        "capture_scope": "before study launch",
        "gpu_count": len(selected),
        "gpu_cli_indices": gpus,
        "physical_gpu_indices": selected,
        "gpus": inventory,
        "runtime": environment(),
        "cpu_logical_count": os.cpu_count(),
        "runtime_scope": "launcher; worker-specific execution environments are exported separately",
        "scoring_packages": {
            name: importlib.metadata.version(name) for name in ("math-verify", "sympy")
        },
        "cpu_architecture": platform.machine(),
        "host_ram_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
        "environment_variables": {
            key: os.environ.get(key)
            for key in ("CUDA_VISIBLE_DEVICES", "VLLM_USE_V1", "OMP_NUM_THREADS")
        },
        "execution": {
            "backend": spec["model"].get("backend"),
            "dtype": spec["model"]["dtype"],
            "model": spec["model"]["name"],
            "revision": spec["model"]["revision"],
            "tensor_parallel_size": 1,
            "gpu_workers": len(selected),
            "max_concurrent_cases_per_gpu": spec["model"].get("vllm_batch_size", 8),
            "vllm_batch_tokens": spec["model"].get("vllm_batch_tokens", 4096),
            "gpu_memory_fraction": spec["model"]["gpu_memory_fraction"],
        },
    }


def export_reports(study, work, output):
    output.mkdir(parents=True, exist_ok=True)
    if "environment" in study:
        atomic_json(output / "environment.json", study["environment"])
    for arm in ("baseline", "ours"):
        lines = [
            f"# {arm}: {study['branch']}",
            "",
            f"Cohort: `{study['cohort_version']}`",
            "",
            "Environment: [environment.json](environment.json): GPU model/count/IDs, driver/CUDA, packages, precision and batching.",
            "",
            "| Dataset | Correct / completed | Required n | Accuracy | Phase wall (s) | Run state |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for task in study.get("benchmarks", list(study["runs"])):
            run_name = study["runs"][task]
            run = work / "outputs" / run_name
            report_path = run / "report.json"
            report = json.loads(report_path.read_text()) if report_path.exists() else {}
            score = report.get("own", {}).get(arm, {}).get(task, {})
            n, correct = score.get("n", 0), score.get("correct", 0)
            status_path = run / "status.json"
            status = (
                json.loads(status_path.read_text())
                if status_path.exists()
                else {"state": "not_started"}
            )
            accuracy = f"{100 * correct / n:.2f}%" if n else "not measured"
            phase_seconds = "not measured"
            schedule_path, end_path = run / "schedule.json", run / f"{arm}-complete.json"
            if schedule_path.exists() and end_path.exists():
                schedule = json.loads(schedule_path.read_text())
                end = json.loads(end_path.read_text())
                if arm in schedule and "at" in end:
                    phase_seconds = f"{datetime.fromisoformat(end['at']).timestamp() - schedule[arm]['start_epoch']:.1f}"
            lines.append(
                f"| {task} | {correct}/{n} | {study['counts'][task]} | {accuracy} | {phase_seconds} | {status['state']} |"
            )
            if status.get("audits_passed"):
                dest = output / "reports" / task
                dest.mkdir(parents=True, exist_ok=True)
                for name in ("report.json", "status.json"):
                    (dest / name).write_bytes((run / name).read_bytes())
                workers = {}
                for identity in sorted(run.glob("workers/*/identity.json")):
                    record = json.loads(identity.read_text())
                    workers[identity.parent.name] = {
                        "assignment": record["assignment"],
                        "runtime": record["environment"],
                        "identity_sha256": file_digest(identity),
                    }
                atomic_json(dest / "worker-environments.json", workers)
        lines += [
            "",
            "Incomplete runs and samples are not full-dataset accuracy.",
            "Timing source: each saved report/schedule/arm-complete file; report loading/audit exclusions.",
            "",
        ]
        (output / f"{arm}.md").write_text("\n".join(lines))
    method = [
        f"# Method: {study['branch']}",
        "",
        "## Hypothesis",
        "",
        study["hypothesis"],
        "",
        "## Implementation",
        "",
        study["method_description"],
        "",
        f"Code branch: `{study['branch']}`; commit: `{study.get('code_commit', 'not recorded')}`.",
        f"Canonical shared checkout commit: `{study.get('shared_commit', 'not recorded')}`.",
        "",
        "Baseline is plain_ar; ours is filtered_futures. Both use the same backend, model,",
        "prompts, frozen IDs, per-case seeds, repetition guard and output budget.",
        "",
        f"Cohort manifest SHA256: `{study['cohort_manifest_sha256']}`",
        "",
        "## Frozen configuration",
        "",
        "```json",
        json.dumps(public_study(study)["spec"], indent=2),
        "```",
        "",
        "## Source identity",
        "",
        "```json",
        json.dumps(study["source"], indent=2),
        "```",
        "",
    ]
    method += [
        "## Environment",
        "",
        "See [environment.json](environment.json) and per-run",
        "`reports/<task>/worker-environments.json` for exact GPU allocation and runtime versions.",
        "",
    ]
    (output / "method.md").write_text("\n".join(method))
    atomic_json(output / "study-plan.json", public_study(study))
    rows = []
    for task in study.get("benchmarks", list(study["runs"])):
        run = work / "outputs" / study["runs"][task]
        report_path, status_path = run / "report.json", run / "status.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
        scores = {}
        for arm in ("baseline", "ours"):
            score = report.get("own", {}).get(arm, {}).get(task, {})
            scores[arm] = {"n": score.get("n", 0), "correct": score.get("correct", 0)}
        rows.append(
            {
                "dataset": task,
                "n_required": study["counts"][task],
                "method": "filtered_futures/" + study["spec"]["experiment"]["selection"],
                "baseline": scores["baseline"],
                "ours": scores["ours"],
                "audits_passed": bool(status.get("audits_passed")),
                "gpu_count": study.get("environment", {}).get("gpu_count"),
                "gpu_model": "; ".join(
                    sorted({g["name"] for g in study.get("environment", {}).get("gpus", [])})
                ),
            }
        )
    atomic_json(
        output / "submission.json",
        {
            "id": study["branch"],
            "code_branch": study["branch"],
            "code_commit": study.get("code_commit"),
            "cohort_version": study["cohort_version"],
            "cohort_manifest_sha256": study["cohort_manifest_sha256"],
            "scope": "shared",
            "model": study["spec"]["model"]["name"],
            "model_revision": study["spec"]["model"]["revision"],
            "backend": study["spec"]["model"].get("backend"),
            "dtype": study["spec"]["model"]["dtype"],
            "scorer_sha256": digest(
                {
                    key: study["source"].get(key)
                    for key in ("lost_tokens/core.py", "lost_tokens/math_scoring.py")
                }
            ),
            "evaluation_settings_sha256": digest(
                {
                    "prompt_limit": study["spec"]["data"]["prompt_limit"],
                    **{
                        key: study["spec"]["experiment"][key]
                        for key in (
                            "max_output_tokens",
                            "temperature",
                            "top_k",
                            "top_p",
                            "repetition_guard",
                        )
                    },
                }
            ),
            "seed": study["spec"]["experiment"]["seed"],
            "rows": rows,
        },
    )


def public_study(study):
    result = json.loads(json.dumps(study))
    result["spec"]["model"]["cache_dir"] = "<MODEL_CACHE>"
    result["spec"]["similarity"]["encoder"]["cache_dir"] = "<MODEL_CACHE>"
    result["runtime_paths_redacted"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "run", "report"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--date", default=datetime.now().astimezone().date().isoformat())
    parser.add_argument("--work-dir", type=Path, default=Path("workspace"))
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument(
        "--shared-root",
        type=Path,
        default=SHARED_ROOT,
        help="Read-only shared-evaluation checkout containing the frozen cohort",
    )
    parser.add_argument("--config", type=Path, default=REPO / "configs/vllm-argmax.json")
    parser.add_argument(
        "--gpus", default="0", help="Explicit visible GPU indices; defaults to one GPU"
    )
    parser.add_argument(
        "--benchmarks", nargs="+", default=["aime25", "hmmt25", "gsm8k", "gpqa", "math500", "mmlu"]
    )
    parser.add_argument("--method-description")
    parser.add_argument("--hypothesis")
    args = parser.parse_args()
    shared_root = args.shared_root.resolve()
    cohort = shared_root / "evaluation/subsets/shared-v1"
    if not (cohort / "manifest.json").exists():
        parser.error(
            "Fetch shared-evaluation into .shared-evaluation (or pass --shared-root); see CLAUDE.md"
        )
    branch = f"{args.name}-{args.date}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*-\d{4}-\d{2}-\d{2}", branch):
        parser.error("Expected {name}-{YYYY-MM-DD} using an ASCII name")
    tasks = list(dict.fromkeys(args.benchmarks))
    known = json.loads((cohort / "manifest.json").read_text())["datasets"]
    if not tasks or any(task not in known for task in tasks):
        parser.error("Only the six shared-v1 benchmark tasks are allowed")
    work = args.work_dir.resolve()
    spec = runtime_spec(load_spec(args.config), work, args.model_cache)
    plan_path = work / "shared-studies" / branch / "study-plan.json"
    output = plan_path.parent / "submission"
    if args.action == "report":
        study = json.loads(plan_path.read_text())
        export_reports(study, work, output)
        return
    if args.action == "prepare":
        download_datasets(work, tasks)
        download_models(spec)
        prepare(work, spec, tasks)
    manifest = verify_cohort(work, spec, tasks, cohort)
    print(
        "Verified fixed cohorts:",
        {task: manifest["datasets"][task]["n"] for task in tasks},
        flush=True,
    )
    if args.action != "run":
        return
    actual_branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPO, text=True
    ).strip()
    if actual_branch != branch:
        parser.error(f"Checkout {branch} before running; current branch is {actual_branch}")
    if spec["model"].get("backend") != "vllm" or spec["experiment"]["seed"] != 95021:
        parser.error("Shared-v1 requires vLLM and experiment.seed=95021")
    gpu_rows = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,utilization.gpu", "--format=csv"],
        text=True,
    )
    print(gpu_rows, flush=True)
    require_free_gpus(args.gpus)
    launch_environment = collect_environment(args.gpus, spec)
    if plan_path.exists():
        study = json.loads(plan_path.read_text())
        if (
            study["spec"] != spec
            or study["source"] != source_fingerprint()
            or study["gpus"] != args.gpus
            or study.get("benchmarks", list(study["runs"])) != tasks
            or study["cohort_manifest_sha256"] != file_digest(cohort / "manifest.json")
        ):
            parser.error(
                "Frozen study changed; restore original source/config/environment or use a new branch/date"
            )
        resume_capture = (
            plan_path.parent / f"environment-resume-{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
        )
        atomic_json(resume_capture, launch_environment)
        output.mkdir(parents=True, exist_ok=True)
        atomic_json(output / resume_capture.name, launch_environment)
    else:
        if not args.method_description or not args.hypothesis:
            parser.error("New studies require --method-description and --hypothesis")
        dirty = subprocess.check_output(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "src",
                "configs",
                "scripts",
                "pyproject.toml",
                "uv.lock",
            ],
            cwd=REPO,
            text=True,
        ).strip()
        if dirty:
            parser.error("Commit the personal implementation/settings before starting a new study")
        study = {
            "branch": branch,
            "cohort_version": manifest["version"],
            "cohort_manifest_sha256": file_digest(cohort / "manifest.json"),
            "shared_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=shared_root, text=True
            ).strip(),
            "code_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
            ).strip(),
            "spec": spec,
            "source": source_fingerprint(),
            "gpus": args.gpus,
            "benchmarks": tasks,
            "method_description": args.method_description,
            "hypothesis": args.hypothesis,
            "environment": launch_environment,
            "counts": {task: manifest["datasets"][task]["n"] for task in tasks},
            "runs": {task: f"{branch}-shared-v1-{task}" for task in tasks},
        }
        atomic_json(plan_path, study)
    for task in study["benchmarks"]:
        run_name = study["runs"][task]
        run = work / "outputs" / run_name
        command = [sys.executable, "-u", "-m", "lost_tokens"]
        if run.exists():
            command += ["resume", "--run", str(run)]
        else:
            command += [
                "run",
                "--config",
                str(args.config.resolve()),
                "--work-dir",
                str(work),
                "--benchmarks",
                task,
                "--gpus",
                args.gpus,
                "--arms",
                "baseline",
                "ours",
                "--run-name",
                run_name,
                "--ids-file",
                str(cohort / f"{task}.json"),
            ]
            if args.model_cache:
                command += ["--model-cache", str(args.model_cache.resolve())]
        try:
            subprocess.run(command, cwd=REPO, check=True)
        finally:
            export_reports(study, work, output)
    print("Finished and exported:", output, flush=True)


if __name__ == "__main__":
    main()
