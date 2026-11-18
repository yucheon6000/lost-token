import importlib.util
from pathlib import Path
import tempfile
import unittest

from lost_tokens.core import atomic_json

loader = importlib.util.spec_from_file_location(
    "freeze_legacy_comparison",
    Path(__file__).resolve().parents[1] / "scripts/freeze_legacy_comparison.py",
)
comparison = importlib.util.module_from_spec(loader)
loader.loader.exec_module(comparison)


class LegacyComparisonTests(unittest.TestCase):
    def test_existing_choice_prediction_and_math_grade_do_not_need_new_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "workers/one/outcomes/mmlu/one.json"
            atomic_json(
                p, {"id": "one", "task": "mmlu", "prediction": "B", "correct": True, "gold": "B"}
            )
            row = comparison.rescore_outcome(
                p, {"answer_format": "choice", "choices": list("ABCD")}
            )
            self.assertEqual(row["prediction"], "B")
            self.assertTrue(row["correct"])
            row = comparison.rescore_outcome(p, {"answer_format": "math", "choices": []})
            self.assertTrue(row["correct"])

    def test_missing_choice_uses_final_response_not_gold_or_scratchpad(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workers/one"
            p = root / "outcomes/mmlu/one.json"
            atomic_json(
                p, {"id": "one", "task": "mmlu", "prediction": None, "correct": False, "gold": "C"}
            )
            case_path = root / "cases/evaluation/mmlu/one.json"
            for answer, expected in ((r"\boxed{B}", "B"), ("", None)):
                atomic_json(
                    case_path,
                    {
                        "conditions": {
                            "plain_ar": {
                                "prediction": None,
                                "correct": False,
                                "answer_text": answer,
                                "body_text": "Final answer: (C)",
                            }
                        }
                    },
                )
                row = comparison.rescore_outcome(
                    p, {"answer_format": "choice", "choices": list("ABCD")}
                )
                self.assertEqual(row["prediction"], expected)
                self.assertFalse(row["correct"])
