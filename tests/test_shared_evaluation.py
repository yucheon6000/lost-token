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
                "0",
                "--config",
                str(shared.REPO / "configs/vllm-argmax.json"),
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
                "version": "shared-v1",
                "datasets": {"gsm8k": {"n": 1319}, "aime25": {"n": 30}},
            }
            with (
                patch.object(shared, "REPO", work),
                patch.object(shared.sys, "argv", argv),
                patch.object(shared, "verify_cohort", return_value=manifest),
                patch.object(
                    shared, "source_fingerprint", return_value={"generation.py": "frozen"}
                ),
                patch.object(shared, "collect_environment", return_value={"gpu_count": 1}),
                patch.object(shared, "require_free_gpus"),
                patch.object(shared, "export_reports"),
                patch.object(
                    shared.subprocess,
                    "check_output",
                    side_effect=lambda cmd, **kw: "tester-2026-11-15"
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
