import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.config import runtime_spec
from lost_tokens.core import digest, file_digest
from lost_tokens.data import sources


def script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


freeze = script("freeze_shared_subsets")
shared = script("shared_eval")


class SharedEvaluationTests(unittest.TestCase):
    def test_local_submission_exports_and_validates_in_separate_hub(self):
        hub_spec = importlib.util.spec_from_file_location(
            "hub_results", shared.SHARED_ROOT / "tools/results.py"
        )
        hub = importlib.util.module_from_spec(hub_spec)
        hub_spec.loader.exec_module(hub)
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            run = work / "outputs" / "run"
            run.mkdir(parents=True)
            (run / "report.json").write_text(
                json.dumps(
                    {
                        "own": {
                            "baseline": {"aime25": {"correct": 24, "n": 30}},
                            "ours": {"aime25": {"correct": 25, "n": 30}},
                        }
                    }
                )
            )
            (run / "status.json").write_text(
                json.dumps({"state": "complete", "audits_passed": True})
            )
            study = {
                "branch": "tester-2026-11-15",
                "code_commit": "a" * 40,
                "shared_commit": "b" * 40,
                "cohort_version": "shared-v1",
                "cohort_manifest_sha256": file_digest(shared.COHORT / "manifest.json"),
                "spec": runtime_spec(load_spec(shared.REPO / "configs/vllm-argmax.json"), work),
                "source": shared.source_fingerprint(),
                "runs": {"aime25": "run"},
                "benchmarks": ["aime25"],
                "counts": {"aime25": 30},
                "hypothesis": "test",
                "method_description": "test method",
                "environment": {"gpu_count": 1, "gpus": [{"name": "test GPU"}]},
            }
            output = work / "local-submission"
            shared.export_reports(study, work, output)
            metadata = json.loads((output / "submission.json").read_text())
            self.assertEqual(metadata["rows"][0]["ours"]["correct"], 25)
            self.assertEqual(metadata["code_commit"], "a" * 40)
            self.assertNotIn(str(work), (output / "study-plan.json").read_text())
            import shutil

            destination = work / "hub" / "experiment-results" / study["branch"]
            shutil.copytree(output, destination)
            shutil.copytree(shared.COHORT, work / "hub/evaluation/subsets/shared-v1")
            hub.validate(destination, work / "hub")
            md, table = hub.build(work / "hub")
            self.assertIn("83.33% (25/30)", md)
            self.assertIn("80.00% (24/30)", md)

    def test_environment_records_exact_selected_devices_and_omits_secrets(self):
        spec = load_spec()
        with (
            patch("lost_tokens.runner.devices", return_value=["2", "5"]),
            patch(
                "lost_tokens.runtime.environment", return_value={"packages": {}, "gpu": "launcher"}
            ),
            patch.object(
                shared.subprocess,
                "check_output",
                return_value="0, other, UUID0, 100, driver\n2, cardA, UUID2, 200, driver\n5, cardB, UUID5, 300, driver\n",
            ),
            patch.dict(os.environ, {"SECRET_EXAMPLE_TOKEN": "must-not-export"}),
        ):
            result = shared.collect_environment("0,1", spec)
        self.assertEqual(result["gpu_count"], 2)
        self.assertEqual(result["physical_gpu_indices"], ["2", "5"])
        self.assertEqual([gpu["name"] for gpu in result["gpus"]], ["cardA", "cardB"])
        self.assertNotIn("SECRET_EXAMPLE_TOKEN", json.dumps(result))

    def test_study_resume_retains_non_alphabetical_dataset_order(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            commands = []
            argv = [
                "shared_eval.py",
                "run",
                "--name",
                "tester",
                "--date",
                "2026-11-15",
                "--work-dir",
                folder,
                "--gpus",
                "0,1,2,3",
                "--profile",
                "l40s-4gpu",
                "--config",
                str(shared.REPO / "configs/vllm-argmax.json"),
                "--shared-root",
                str(shared.SHARED_ROOT.resolve()),
                "--benchmarks",
                "gsm8k",
                "aime25",
                "--method-description",
                "test method",
                "--hypothesis",
                "test hypothesis",
            ]

            def execute(command, **kwargs):
                commands.append(command)
                if "--run-name" in command:
                    (work / "outputs" / command[command.index("--run-name") + 1]).mkdir(
                        parents=True
                    )
                return SimpleNamespace(returncode=0)

            manifest = {
                "version": "l40s-2h-v1",
                "datasets": {"gsm8k": {"n": 1319}, "aime25": {"n": 30}},
            }
            with (
                patch.object(shared, "REPO", work),
                patch.object(shared.sys, "argv", argv),
                patch.object(shared, "verify_cohort", return_value=manifest),
                patch.object(
                    shared, "source_fingerprint", return_value={"generation.py": "frozen"}
                ),
                patch.object(
                    shared,
                    "collect_environment",
                    return_value={
                        "gpu_count": 4,
                        "gpus": [{"name": "NVIDIA L40S"}] * 4,
                        "execution": {},
                    },
                ),
                patch.object(shared, "require_free_gpus"),
                patch.object(shared, "export_reports"),
                patch.object(
                    shared.subprocess,
                    "check_output",
                    side_effect=lambda cmd, **kw: (
                        "tester-2026-11-15"
                        if cmd[:2] == ["git", "branch"]
                        else ("" if cmd[:2] == ["git", "status"] else "a" * 40)
                    )
                    if cmd[0] == "git"
                    else "GPU inventory",
                ),
                patch.object(shared.subprocess, "run", side_effect=execute),
            ):
                shared.main()
                shared.main()
            self.assertEqual(len(commands), 4)
            self.assertTrue(all("resume" in cmd for cmd in commands[2:]))
            plan = json.loads(
                (work / "shared-studies/tester-2026-11-15/study-plan.json").read_text()
            )
            self.assertEqual(plan["benchmarks"], ["gsm8k", "aime25"])
            self.assertEqual(plan["hardware_profile"], "l40s-4gpu")
            self.assertEqual(plan["task_specs"]["aime25"]["model"]["vllm_batch_size"], 4)
            self.assertEqual(plan["task_specs"]["gsm8k"]["model"]["vllm_batch_size"], 8)
            self.assertTrue(all("l40s-2h-v1" in name for name in plan["runs"].values()))
            for task in plan["benchmarks"]:
                config = work / "shared-studies/tester-2026-11-15/task-configs" / f"{task}.json"
                self.assertEqual(json.loads(config.read_text()), plan["task_specs"][task])

    def test_hardware_profiles_select_immutable_cohorts_and_task_batches(self):
        spec = load_spec(shared.REPO / "configs/vllm-argmax.json")
        original = copy.deepcopy(spec)
        l40s, cohort = shared.load_profile(shared.SHARED_ROOT, "l40s-4gpu")
        self.assertEqual(cohort.name, "l40s-2h-v1")
        configs = shared.task_specs(spec, ["aime25", "hmmt25", "mmlu"], l40s)
        self.assertEqual([configs[t]["model"]["vllm_batch_size"] for t in configs], [4, 4, 8])
        self.assertEqual(spec, original)
        pro, cohort = shared.load_profile(shared.SHARED_ROOT, "pro6000-8gpu")
        self.assertEqual(cohort.name, "shared-v1")
        self.assertTrue(
            all(
                c["model"]["vllm_batch_size"] == 8
                for c in shared.task_specs(spec, ["aime25", "mmlu"], pro).values()
            )
        )
        shared.verify_hardware(l40s, {"gpu_count": 4, "gpus": [{"name": "NVIDIA L40S"}] * 4})
        for environment in (
            {"gpu_count": 8, "gpus": [{"name": "NVIDIA L40S"}] * 8},
            {"gpu_count": 4, "gpus": [{"name": "NVIDIA RTX PRO 6000 Blackwell"}] * 4},
        ):
            with self.assertRaises(ValueError):
                shared.verify_hardware(l40s, environment)
        with self.assertRaises(ValueError):
            shared.load_profile(shared.SHARED_ROOT, "unknown")

    def test_explicit_ours_only_without_reference_never_launches_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            _, cohort = shared.load_profile(shared.SHARED_ROOT, "l40s-4gpu")
            manifest = json.loads((cohort / "manifest.json").read_text())
            env = {"gpu_count": 4, "gpus": [{"name": "NVIDIA L40S"}] * 4, "execution": {}}
            commands = []
            argv = [
                "shared_eval.py",
                "run",
                "--name",
                "tester",
                "--date",
                "2026-11-15",
                "--work-dir",
                folder,
                "--profile",
                "l40s-4gpu",
                "--gpus",
                "0,1,2,3",
                "--shared-root",
                str(shared.SHARED_ROOT.resolve()),
                "--benchmarks",
                "aime25",
                "--config",
                str(shared.REPO / "configs/vllm-ours.json"),
                "--arms",
                "ours",
                "--allow-unmeasured-baseline",
                "--method-description",
                "ours only",
                "--hypothesis",
                "evaluate absolute accuracy",
            ]
            with (
                patch.object(shared, "REPO", work),
                patch.object(shared.sys, "argv", argv),
                patch.object(shared, "verify_cohort", return_value=manifest),
                patch.object(shared, "source_fingerprint", return_value={"generation.py": "fixed"}),
                patch.object(shared, "collect_environment", return_value=env),
                patch.object(shared, "require_free_gpus"),
                patch.object(shared, "export_reports"),
                patch.object(
                    shared.subprocess,
                    "check_output",
                    side_effect=lambda cmd, **kw: "tester-2026-11-15"
                    if cmd[:2] == ["git", "branch"]
                    else ("" if cmd[:2] == ["git", "status"] else "a" * 40),
                ),
                patch.object(
                    shared.subprocess, "run", side_effect=lambda cmd, **kw: commands.append(cmd)
                ),
            ):
                shared.main()
            self.assertEqual(len(commands), 1)
            command = commands[0]
            self.assertEqual(
                command[command.index("--arms") + 1 : command.index("--run-name")], ["ours"]
            )
            plan = json.loads(
                (work / "shared-studies/tester-2026-11-15/study-plan.json").read_text()
            )
            self.assertIsNone(plan["baseline_reference"])
            self.assertTrue(plan["allow_unmeasured_baseline"])

    def test_profile_manifest_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "evaluation/profiles.json"
            path.parent.mkdir(parents=True)
            path.write_bytes((shared.SHARED_ROOT / "evaluation/profiles.json").read_bytes())
            manifest = root / "evaluation/subsets/l40s-2h-v1/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"version":"l40s-2h-v1"}')
            with self.assertRaises(ValueError):
                shared.load_profile(root, "l40s-4gpu")

    def test_ours_only_launch_reuses_reference_and_never_schedules_baseline(self):
        from lost_tokens import frozen_baseline

        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            profile, cohort = shared.load_profile(shared.SHARED_ROOT, "l40s-4gpu")
            manifest = json.loads((cohort / "manifest.json").read_text())
            env = {"gpu_count": 4, "gpus": [{"name": "NVIDIA L40S"}] * 4, "execution": {}}
            spec = runtime_spec(load_spec(shared.REPO / "configs/vllm-argmax.json"), work)
            source = {"generation.py": "frozen"}
            stub = {
                "spec": spec,
                "task_specs": shared.task_specs(spec, ["aime25"], profile),
                "cohort_version": manifest["version"],
                "cohort_manifest_sha256": file_digest(cohort / "manifest.json"),
                "hardware_profile": "l40s-4gpu",
                "source": source,
                "environment": env,
            }
            ids = json.loads((cohort / "aime25.json").read_text())["ids"]
            payload = {
                "conditions": frozen_baseline.conditions(stub),
                "counts": {"aime25": 30},
                "outcomes": {
                    "aime25": [{"task": "aime25", "id": ident, "correct": True} for ident in ids]
                },
                "origin": {
                    "branch": "tester-base-2026-11-15",
                    "code_commit": "b" * 40,
                    "tasks": {"aime25": {"phase_seconds": 120}},
                },
            }
            reference = work / "baseline-reference.json"
            reference.write_text(json.dumps({"payload": payload, "sha256": digest(payload)}))
            commands = []
            argv = [
                "shared_eval.py",
                "run",
                "--name",
                "tester",
                "--date",
                "2026-11-15",
                "--work-dir",
                folder,
                "--profile",
                "l40s-4gpu",
                "--gpus",
                "0,1,2,3",
                "--shared-root",
                str(shared.SHARED_ROOT.resolve()),
                "--benchmarks",
                "aime25",
                "--arms",
                "ours",
                "--baseline-ref",
                str(reference),
                "--config",
                str(shared.REPO / "configs/vllm-argmax.json"),
                "--method-description",
                "new ours",
                "--hypothesis",
                "test",
            ]
            with (
                patch.object(shared, "REPO", work),
                patch.object(shared.sys, "argv", argv),
                patch.object(shared, "verify_cohort", return_value=manifest),
                patch.object(shared, "source_fingerprint", return_value=source),
                patch.object(shared, "collect_environment", return_value=env),
                patch.object(shared, "require_free_gpus"),
                patch.object(shared, "export_reports"),
                patch.object(
                    shared.subprocess,
                    "check_output",
                    side_effect=lambda cmd, **kw: "tester-2026-11-15"
                    if cmd[:2] == ["git", "branch"]
                    else ("" if cmd[:2] == ["git", "status"] else "a" * 40),
                ),
                patch.object(
                    shared.subprocess,
                    "run",
                    side_effect=lambda command, **kw: commands.append(command),
                ),
            ):
                shared.main()
            self.assertEqual(len(commands), 1)
            cmd = commands[0]
            self.assertEqual(cmd[cmd.index("--arms") + 1 : cmd.index("--run-name")], ["ours"])
            plan = json.loads(
                (work / "shared-studies/tester-2026-11-15/study-plan.json").read_text()
            )
            self.assertEqual(plan["baseline_reference"]["sha256"], digest(payload))
            # Exercise the real Markdown/submission export and hub validation too.
            run = work / "outputs" / plan["runs"]["aime25"]
            run.mkdir(parents=True)
            (run / "plan.json").write_text(
                json.dumps({"arms": ["ours"], "workers": [{"name": "ours-worker0", "arm": "ours"}]})
            )
            outcomes = run / "workers/ours-worker0/outcomes/aime25"
            outcomes.mkdir(parents=True)
            for ident in ids:
                (outcomes / f"{ident}.json").write_text(
                    json.dumps(
                        {
                            "task": "aime25",
                            "id": ident,
                            "correct": True,
                            "finished_epoch": 110,
                        }
                    )
                )
            (run / "report.json").write_text(
                json.dumps({"own": {"ours": {"aime25": {"n": 30, "correct": 30}}}})
            )
            (run / "status.json").write_text(
                json.dumps({"state": "complete", "audits_passed": True})
            )
            output = work / "submission"
            shared.export_reports(plan, work, output)
            metadata = json.loads((output / "submission.json").read_text())
            self.assertEqual(metadata["baseline_reference_sha256"], digest(payload))
            self.assertEqual(metadata["rows"][0]["baseline"], {"n": 30, "correct": 30})
            self.assertIn(
                "Paired against the same frozen AR baseline", (output / "ours.md").read_text()
            )
            self.assertNotIn(str(reference), (output / "study-plan.json").read_text())
            import shutil

            destination = work / "hub/experiment-results/tester-2026-11-15"
            shutil.copytree(output, destination)
            shutil.copytree(cohort, work / "hub/evaluation/subsets/l40s-2h-v1")
            (work / "hub/evaluation/profiles.json").write_bytes(
                (shared.SHARED_ROOT / "evaluation/profiles.json").read_bytes()
            )
            tool_spec = importlib.util.spec_from_file_location(
                "hub_export_test", shared.SHARED_ROOT / "tools/results.py"
            )
            hub = importlib.util.module_from_spec(tool_spec)
            tool_spec.loader.exec_module(hub)
            hub.validate(destination, work / "hub")

    def test_selection_is_order_independent_and_label_blind(self):
        rows = [{"id": str(i), "subject": "a" if i < 5 else "b", "gold": "A"} for i in range(12)]
        selected = freeze.select_rows(rows, "test", 5, ("subject",))
        changed = [dict(r, gold="B") for r in reversed(rows)]
        self.assertEqual(
            [r["id"] for r in selected],
            [r["id"] for r in freeze.select_rows(changed, "test", 5, ("subject",))],
        )
        self.assertEqual(len(selected), 5)
        with self.assertRaises(ValueError):
            freeze.select_rows(rows + [rows[0]], "test", 5, ())

    def test_committed_manifest_has_required_counts_and_id_integrity(self):
        manifest = json.loads((shared.COHORT / "manifest.json").read_text())
        expected = {
            "aime25": 30,
            "hmmt25": 30,
            "gsm8k": 1319,
            "gpqa": 448,
            "math500": 250,
            "mmlu": 3511,
        }
        for task, n in expected.items():
            entry = manifest["datasets"][task]
            path = shared.COHORT / entry["ids_file"]
            ids = json.loads(path.read_text())["ids"]
            self.assertEqual(len(ids), n)
            self.assertEqual(len(set(ids)), n)
            self.assertEqual(file_digest(path), entry["ids_file_sha256"])
            self.assertEqual(digest(ids), entry["ids_sha256"])
            self.assertEqual(sum(entry["strata_counts"].values()), n)

    def test_verification_rejects_changed_ids_or_question_content(self):
        spec = load_spec()
        rows = [{"id": str(i), "question": "Q", "gold": "A"} for i in range(4)]
        with tempfile.TemporaryDirectory() as folder:
            cohort = Path(folder)
            ids = ["0", "2"]
            path = cohort / "mmlu.json"
            path.write_text(json.dumps({"ids": ids}))
            manifest = {
                "data": spec["data"],
                "model": {k: spec["model"][k] for k in ("name", "revision", "enable_thinking")},
                "data_adapter_sha256": file_digest(shared.REPO / "src/lost_tokens/data.py"),
                "datasets": {
                    "mmlu": {
                        "ids_file": path.name,
                        "ids_file_sha256": file_digest(path),
                        "ids_sha256": digest(ids),
                        "full_n": 4,
                        "n": 2,
                        "selected_rows_sha256": digest([rows[0], rows[2]]),
                        "source_definition_sha256": digest(sources()["mmlu"]),
                    }
                },
            }
            (cohort / "manifest.json").write_text(json.dumps(manifest))
            with patch.object(shared, "load_prepared", return_value=rows):
                shared.verify_cohort(folder, spec, ["mmlu"], cohort)
                altered = copy.deepcopy(rows)
                altered[0]["question"] = "changed"
                with patch.object(shared, "load_prepared", return_value=altered):
                    with self.assertRaises(ValueError):
                        shared.verify_cohort(folder, spec, ["mmlu"], cohort)
                path.write_text(json.dumps({"ids": ["1", "2"]}))
                with self.assertRaises(ValueError):
                    shared.verify_cohort(folder, spec, ["mmlu"], cohort)
