"""Guard against confounded controls and misleading partial-cohort comparisons."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from lost_tokens.config import load_spec


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verification_study", ROOT / "scripts/run_verification_study.py"
)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class VerificationStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_frozen_pairs_only_change_verification_and_keep_original_sampling(self):
        pipeline = json.loads((ROOT / "configs/verification-study.json").read_text())
        self.assertEqual(set(pipeline["condition_order"]), {"control", "verification"})
        for task, pair in pipeline["configs_by_task"].items():
            with self.subTest(task=task):
                study.validate_pair(ROOT / pair["control"], ROOT / pair["verification"])
                cfg = load_spec(ROOT / pair["verification"])
                self.assertEqual(cfg["experiment"]["max_output_tokens"], 32768)
                self.assertEqual(cfg["experiment"]["seed"], 95021)

    def test_changed_sampling_or_enabled_control_is_rejected(self):
        base = load_spec(ROOT / "configs/vllm-argmax.json")
        verify = load_spec(ROOT / "configs/verification-argmax.json")
        a, b = self.root / "control.json", self.root / "verify.json"
        a.write_text(json.dumps(base))
        verify["experiment"]["temperature"] = 0.8
        b.write_text(json.dumps(verify))
        with self.assertRaises(ValueError):
            study.validate_pair(a, b)
        verify["experiment"]["temperature"] = base["experiment"]["temperature"]
        b.write_text(json.dumps(verify))
        base["experiment"]["disagreement_verification"] = copy.deepcopy(
            verify["experiment"]["disagreement_verification"]
        )
        a.write_text(json.dumps(base))
        with self.assertRaises(ValueError):
            study.validate_pair(a, b)

    def test_partial_report_compares_only_identical_completed_ids(self):
        run = self.root / "run"
        out = run / "workers/ours-worker0/outcomes/task"
        out.mkdir(parents=True)
        (out / "one.json").write_text(
            json.dumps({"id": "one", "task": "task", "arm": "ours", "correct": True})
        )
        manifest = {
            "cohort": {"task": {"ids": ["one", "two"]}},
            "comparison": {
                "task": {"baseline": {"one": {"correct": False}, "two": {"correct": True}}}
            },
        }
        state = {
            "state": "running",
            "jobs": [
                {
                    "task": "task",
                    "variant": "verification",
                    "state": "running",
                    "run": str(run),
                    "n_required": 2,
                }
            ],
        }
        study.export(self.root, manifest, state)
        job = state["jobs"][0]
        self.assertEqual(
            (job["n"], job["correct"], job["baseline_correct_on_completed"]), (1, 1, 0)
        )
        self.assertEqual((job["wins_baseline"], job["losses_baseline"]), (1, 0))
        self.assertIn("task: 1/2", (self.root / "results.md").read_text())
        (out / "rogue.json").write_text(
            json.dumps({"id": "rogue", "task": "task", "arm": "ours", "correct": True})
        )
        with self.assertRaises(ValueError):
            study.export(self.root, manifest, state)


if __name__ == "__main__":
    unittest.main()
