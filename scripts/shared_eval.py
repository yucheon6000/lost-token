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
from lost_tokens import frozen_baseline


REPO = Path(__file__).resolve().parents[1]
SHARED_ROOT = REPO / ".shared-evaluation"
COHORT = SHARED_ROOT / "evaluation/subsets/shared-v1"


def load_profile(shared_root, name):
    if name is None:
        return None, shared_root / "evaluation/subsets/shared-v1"
    profiles = json.loads((shared_root / "evaluation/profiles.json").read_text())["profiles"]
    if name not in profiles:
        raise ValueError("Unknown hardware profile: " + name)
    profile = profiles[name]
    version = profile["cohort_version"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", version):
        raise ValueError("Invalid registered cohort version")
    cohort = shared_root / "evaluation/subsets" / version
    if file_digest(cohort / "manifest.json") != profile["cohort_manifest_sha256"]:
        raise ValueError("Registered cohort manifest changed")
    if json.loads((cohort / "manifest.json").read_text())["version"] != version:
        raise ValueError("Registered cohort version differs")
    return profile, cohort


def task_specs(spec, tasks, profile):
    result = {}
    for task in tasks:
        cfg = json.loads(json.dumps(spec))
        if profile:
            cfg["model"]["vllm_batch_size"] = profile["batch_size_by_task"].get(
                task, profile["batch_size_per_gpu"]
            )
        result[task] = cfg
    return result


def verify_hardware(profile, environment):
    if profile is None:
        return
    if environment["gpu_count"] != profile["gpu_count"]:
        raise ValueError("GPU count differs from the selected hardware profile")
    names = [gpu["name"] for gpu in environment["gpus"]]
    if len(names) != profile["gpu_count"] or any(
        profile["gpu_name_contains"].casefold() not in name.casefold() for name in names
    ):
        raise ValueError("GPU model differs from the selected hardware profile")


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
    reference = None
    descriptor = study.get("baseline_reference")
    reference_path = output / "baseline-reference.json"
    if descriptor:
        if file_digest(Path(descriptor["path"])) != descriptor["file_sha256"]:
            raise ValueError("Frozen baseline reference file changed")
        reference = frozen_baseline.read_reference(
            descriptor["path"], frozen_baseline.conditions(study)
        )
        if reference_path.exists():
            if frozen_baseline.read_reference(reference_path) != reference:
                raise ValueError("Refusing to replace the saved baseline reference")
        else:
            atomic_json(reference_path, reference)
    elif "baseline" in study.get("arms", ["baseline", "ours"]):
        reference = frozen_baseline.freeze(study, work, reference_path)
    if "environment" in study:
        atomic_json(output / "environment.json", study["environment"])
    for arm in ("baseline", "ours"):
        lines = [
            f"# {arm}: {study['branch']}",
            "",
            f"Cohort: `{study['cohort_version']}`",
            f"Hardware profile: `{study.get('hardware_profile') or 'legacy'}`",
            "",
            "Environment: [environment.json](environment.json): GPU model/count/IDs, driver/CUDA, packages, precision and batching.",
            "",
            "| Dataset | Correct / completed | Required n | Accuracy | Phase wall (s) | Run state |",
            "|---|---:|---:|---:|---:|---|",
        ]
        if reference:
            lines += [
                "",
                f"Frozen AR baseline: `{reference['sha256']}`; original code commit: "
                f"`{reference['payload']['origin']['code_commit']}`.",
                "Baseline times are the original measurement; reuse does not launch AR again.",
                "",
            ]
        for task in study.get("benchmarks", list(study["runs"])):
            run_name = study["runs"][task]
            run = work / "outputs" / run_name
            report_path = run / "report.json"
            report = json.loads(report_path.read_text()) if report_path.exists() else {}
            score = report.get("own", {}).get(arm, {}).get(task, {})
            if reference and arm == "baseline":
                score = frozen_baseline.score(reference, task)
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
            if reference and arm == "baseline":
                phase_seconds = (
                    f"{reference['payload']['origin']['tasks'][task]['phase_seconds']:.1f}"
                )
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
                if reference and "ours" in report.get("own", {}):
                    atomic_json(
                        dest / "comparison.json", frozen_baseline.compare(reference, run, task)
                    )
        if reference and arm == "ours":
            lines += [
                "",
                "## Paired against the same frozen AR baseline",
                "",
                "| Dataset | Common n | Baseline correct | Ours correct | Delta pp | Wins / losses |",
                "|---|---:|---:|---:|---:|---:|",
            ]
            for task, name in study["runs"].items():
                run = work / "outputs" / name
                if not (run / "plan.json").exists():
                    continue
                paired = frozen_baseline.compare(reference, run, task)
                delta = paired["difference_pp"]
                delta_text = f"{delta:+.2f}" if delta is not None else "pending"
                lines.append(
                    f"| {task} | {paired['n']} | {paired['baseline_correct']} | "
                    f"{paired['correct']} | {delta_text} | {paired['wins']} / {paired['losses']} |"
                )
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
        f"Hardware profile: `{study.get('hardware_profile') or 'legacy'}`.",
        "Task-specific resolved configs (including batch size) are in study-plan.json/task_specs.",
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
    if reference:
        method += [
            "## Fixed baseline",
            "",
            f"Reference SHA256: `{reference['sha256']}`; original baseline branch: "
            f"`{reference['payload']['origin']['branch']}`; code commit: "
            f"`{reference['payload']['origin']['code_commit']}`.",
            "This immutable AR reference is reused across ours variants. Its outcomes are not",
            "copied into inference checkpoints. See baseline-reference.json for IDs, outcomes and provenance.",
            "",
        ]
    elif study.get("allow_unmeasured_baseline"):
        method += [
            "## Baseline availability",
            "",
            "AR baseline was not measured or reused in this study. The user explicitly requested ours-only evaluation.",
            "Report ours accuracy on the frozen cohort; do not claim a matched baseline improvement.",
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
        if reference:
            scores["baseline"] = frozen_baseline.score(reference, task)
        elif study.get("allow_unmeasured_baseline"):
            scores["baseline"] = None
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
                "batch_size_per_gpu": study.get("task_specs", {})
                .get(task, study["spec"])["model"]
                .get("vllm_batch_size", 8),
            }
        )
    atomic_json(
        output / "submission.json",
        {
            "id": study["branch"],
            "code_branch": study["branch"],
            "code_commit": study.get("code_commit"),
            "cohort_version": study["cohort_version"],
            "hardware_profile": study.get("hardware_profile"),
            "cohort_manifest_sha256": study["cohort_manifest_sha256"],
            "scope": "shared",
            "baseline_reference_sha256": reference["sha256"] if reference else None,
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
    for spec in [result["spec"], *result.get("task_specs", {}).values()]:
        spec["model"]["cache_dir"] = "<MODEL_CACHE>"
        spec["similarity"]["encoder"]["cache_dir"] = "<MODEL_CACHE>"
    result["runtime_paths_redacted"] = True
    if result.get("baseline_reference"):
        result["baseline_reference"]["path"] = "<FROZEN_BASELINE_REFERENCE>"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "run", "report"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--date", default=datetime.now().astimezone().date().isoformat())
    parser.add_argument("--work-dir", type=Path, default=Path("workspace"))
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument(
        "--arms", nargs="+", choices=("baseline", "ours"), default=["baseline", "ours"]
    )
    parser.add_argument(
        "--baseline-ref",
        type=Path,
        help="Immutable baseline-reference.json from your first study; use with --arms ours",
    )
    parser.add_argument(
        "--allow-unmeasured-baseline",
        action="store_true",
        help="Explicit ours-only evaluation without a reference; report AR as unmeasured",
    )
    parser.add_argument("--profile", help="Registered hardware profile: l40s-4gpu or pro6000-8gpu")
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
    try:
        profile, cohort = load_profile(shared_root, args.profile)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
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
        parser.error("Only tasks in the selected frozen cohort are allowed")
    work = args.work_dir.resolve()
    spec = runtime_spec(load_spec(args.config), work, args.model_cache)
    plan_path = work / "shared-studies" / branch / "study-plan.json"
    output = plan_path.parent / "submission"
    resolved_specs = task_specs(spec, tasks, profile)
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
    if args.baseline_ref and args.arms != ["ours"]:
        parser.error("--baseline-ref requires --arms ours; baseline must not be rerun")
    if args.allow_unmeasured_baseline and (args.arms != ["ours"] or args.baseline_ref):
        parser.error("--allow-unmeasured-baseline requires --arms ours and no --baseline-ref")
    if args.arms == ["ours"] and not args.baseline_ref and not args.allow_unmeasured_baseline:
        parser.error("Ours-only studies require your frozen --baseline-ref")
    if args.profile is None and not plan_path.exists():
        parser.error("New studies require --profile l40s-4gpu or --profile pro6000-8gpu")
    actual_branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=REPO, text=True
    ).strip()
    if actual_branch != branch:
        parser.error(f"Checkout {branch} before running; current branch is {actual_branch}")
    if spec["model"].get("backend") != "vllm" or spec["experiment"]["seed"] != 95021:
        parser.error("Shared evaluation requires vLLM and experiment.seed=95021")
    gpu_rows = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,name,memory.used,utilization.gpu", "--format=csv"],
        text=True,
    )
    print(gpu_rows, flush=True)
    require_free_gpus(args.gpus)
    launch_environment = collect_environment(args.gpus, spec)
    try:
        verify_hardware(profile, launch_environment)
    except ValueError as exc:
        parser.error(str(exc))
    if profile:
        launch_environment["hardware_profile"] = args.profile
        launch_environment["execution"]["batch_size_by_task"] = {
            task: cfg["model"]["vllm_batch_size"] for task, cfg in resolved_specs.items()
        }
    baseline_reference = None
    if args.baseline_ref:
        path = args.baseline_ref.resolve()
        expected = frozen_baseline.conditions(
            {
                "spec": spec,
                "task_specs": resolved_specs,
                "cohort_version": manifest["version"],
                "cohort_manifest_sha256": file_digest(cohort / "manifest.json"),
                "hardware_profile": args.profile,
                "source": source_fingerprint(),
                "environment": launch_environment,
            }
        )
        try:
            reference = frozen_baseline.read_reference(path, expected)
            if any(
                reference["payload"]["counts"].get(t) != manifest["datasets"][t]["n"] for t in tasks
            ):
                raise ValueError("Frozen baseline lacks required tasks or cohort sizes")
        except (ValueError, FileNotFoundError) as exc:
            parser.error(str(exc))
        baseline_reference = {
            "path": str(path),
            "file_sha256": file_digest(path),
            "sha256": reference["sha256"],
        }
    if plan_path.exists():
        study = json.loads(plan_path.read_text())
        if (
            study["spec"] != spec
            or study["source"] != source_fingerprint()
            or study["gpus"] != args.gpus
            or study.get("benchmarks", list(study["runs"])) != tasks
            or study["cohort_manifest_sha256"] != file_digest(cohort / "manifest.json")
            or study.get("hardware_profile") != args.profile
            or study.get("profile_definition") != profile
            or ("task_specs" in study and study["task_specs"] != resolved_specs)
            or study.get("arms", ["baseline", "ours"]) != args.arms
            or study.get("baseline_reference") != baseline_reference
            or study.get("allow_unmeasured_baseline", False) != args.allow_unmeasured_baseline
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
            "hardware_profile": args.profile,
            "profile_definition": profile,
            "task_specs": resolved_specs,
            "arms": args.arms,
            "baseline_reference": baseline_reference,
            "allow_unmeasured_baseline": args.allow_unmeasured_baseline,
            "source": source_fingerprint(),
            "gpus": args.gpus,
            "benchmarks": tasks,
            "method_description": args.method_description,
            "hypothesis": args.hypothesis,
            "environment": launch_environment,
            "counts": {task: manifest["datasets"][task]["n"] for task in tasks},
            "runs": {task: f"{branch}-{manifest['version']}-{task}" for task in tasks},
        }
        atomic_json(plan_path, study)
    for task in study["benchmarks"]:
        task_config = args.config.resolve()
        if "task_specs" in study:
            task_config = plan_path.parent / "task-configs" / f"{task}.json"
            expected = study["task_specs"][task]
            if task_config.exists():
                if json.loads(task_config.read_text()) != expected:
                    parser.error("Frozen task config changed: " + task)
            else:
                atomic_json(task_config, expected)
        run_name = study["runs"][task]
        run = work / "outputs" / run_name
        command = [sys.executable, "-u", "-m", "lost_tokens"]
        if run.exists():
            command += ["resume", "--run", str(run)]
        else:
            command += [
                "run",
                "--config",
                str(task_config),
                "--work-dir",
                str(work),
                "--benchmarks",
                task,
                "--gpus",
                args.gpus,
                "--arms",
                *study.get("arms", ["baseline", "ours"]),
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
