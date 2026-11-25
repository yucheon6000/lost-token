"""No best-score selection or accidental MMLU scope expansion."""

import copy
import importlib.util
from pathlib import Path
import unittest

from lost_tokens.config import load_spec

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location(
    "five_priority_tests", ROOT / "scripts/run_five_benchmarks.py"
)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class FiveBenchmarksTests(unittest.TestCase):
    def test_exact_five_full_cohorts_and_native_argmax_are_required(self):
        p = study.read(ROOT / "configs/argmax-five-benchmarks.json")
        cfg = load_spec(ROOT / "configs/vllm-argmax.json")
        study.validate_protocol(p, cfg)
        for key, value in (
            ("benchmarks", p["benchmarks"] + ["mmlu"]),
            ("seeds", p["seeds"][:3]),
            ("cohort", "pilot"),
        ):
            modified = copy.deepcopy(p)
            modified[key] = value
            with self.assertRaises(ValueError):
                study.validate_protocol(modified, cfg)
        with self.assertRaises(ValueError):
            study.validate_protocol(p, load_spec(ROOT / "configs/vllm-lookahead.json"))

    def test_partial_or_unaudited_results_cannot_replace_completed_results(self):
        done = {
            "seed": 42,
            "task": "math500",
            "arm": "ours",
            "state": "complete",
            "audits_passed": True,
            "outcomes_sha256": "fixed",
            "correct": 490,
        }
        partial = {**done, "state": "running", "correct": 499, "outcomes_sha256": "partial"}
        unaudited = {**partial, "state": "complete", "audits_passed": False}
        chosen = study.choose_completed(
            [{"jobs": [partial, unaudited]}, {"jobs": [done]}], (42, "math500", "ours")
        )
        self.assertEqual(chosen, done)
        self.assertIsNone(study.choose_completed([{"jobs": [partial]}], (42, "math500", "ours")))

    def test_conflicting_completed_results_are_rejected_instead_of_selecting_best(self):
        done = {
            "seed": 42,
            "task": "math500",
            "arm": "ours",
            "state": "complete",
            "audits_passed": True,
            "outcomes_sha256": "fixed",
            "correct": 490,
        }
        other = {**done, "outcomes_sha256": "different", "correct": 499}
        with self.assertRaises(ValueError):
            study.choose_completed([{"jobs": [done]}, {"jobs": [other]}], (42, "math500", "ours"))


if __name__ == "__main__":
    unittest.main()
