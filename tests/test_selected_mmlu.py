"""The MMLU follow-up must retain the previously selected seed identities."""

import copy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location(
    "selected_mmlu_tests", ROOT / "scripts/run_selected_mmlu.py"
)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class SelectedMMLUTests(unittest.TestCase):
    def test_seed_choice_and_full_mmlu_scope_are_frozen(self):
        p = study.read(ROOT / "configs/argmax-selected-mmlu.json")
        cfg = load_spec(ROOT / "configs/vllm-argmax.json")
        selection = {
            "selected": {"seeds": [95021, 95022, 95023]},
            "benchmarks": ["aime25", "hmmt25", "gpqa", "gsm8k", "math500"],
        }
        study.validate_protocol(p, cfg, selection)
        for key, value in (
            ("seeds", [95021, 95022, 42]),
            ("benchmarks", ["mmlu", "gpqa"]),
            ("cohort", "shared-v1"),
        ):
            changed = copy.deepcopy(p)
            changed[key] = value
            with self.assertRaises(ValueError):
                study.validate_protocol(changed, cfg, selection)
        with self.assertRaises(ValueError):
            study.validate_protocol(p, load_spec(ROOT / "configs/vllm-lookahead.json"), selection)

    def test_incomplete_new_seed_cannot_enter_combined_report(self):
        seeds = [95021, 95022, 95023]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selection = root / "selection.json"
            atomic_json(selection, {"selected": {"seeds": seeds, "rows": []}})
            m = {
                "pipeline": {"seeds": seeds, "historical_seed": 95021},
                "cohort": {"mmlu": {"n": 10}},
            }
            jobs = []
            for seed in seeds[:2]:
                for arm in ("baseline", "ours"):
                    jobs.append(
                        {
                            "task": "mmlu",
                            "seed": seed,
                            "arm": arm,
                            "n": 10,
                            "correct": 8,
                            "state": "complete",
                            "audits_passed": True,
                            "gains": 1,
                            "losses": 1,
                        }
                    )
            study.base.TASKS = ("mmlu",)
            args = SimpleNamespace(selected_report=selection, study=root)
            with self.assertRaisesRegex(ValueError, "three audited"):
                study.combined_report(args, m, {"jobs": jobs})
            for arm, correct in (("baseline", 8), ("ours", 9)):
                jobs.append(
                    {
                        "task": "mmlu",
                        "seed": 95023,
                        "arm": arm,
                        "n": 10,
                        "correct": correct,
                        "state": "complete",
                        "audits_passed": True,
                        "gains": 1,
                        "losses": 0,
                    }
                )
            study.combined_report(args, m, {"jobs": jobs})
            result = study.read(root / "combined-report.json")
            self.assertEqual(result["seeds"], seeds)
            self.assertEqual(result["rows"][-1]["evaluations_per_arm"], 30)
            self.assertEqual(result["rows"][-1]["baseline_correct"], 24)
            self.assertEqual(result["rows"][-1]["ours_correct"], 25)


if __name__ == "__main__":
    unittest.main()
