import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "rescore_choices", Path(__file__).resolve().parents[1] / "scripts/rescore_choices.py"
)
rescore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescore)


class RescoreChoiceTests(unittest.TestCase):
    def test_optional_math_rescore_uses_question_and_final_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cases = root / "workers/worker0/cases/evaluation/math500"
            cases.mkdir(parents=True)
            record = {
                "task": "math500",
                "id": "one",
                "answer_format": "math",
                "question": "For which grade is the count closest?",
                "gold": "12",
                "conditions": {
                    "plain_ar": {
                        "answer_text": r"\boxed{12^{\text{th}}}",
                        "prediction": r"12^{\text{th}}",
                        "correct": False,
                    }
                },
            }
            (cases / "one.json").write_text(json.dumps(record))
            result = rescore.rescore_run(root, include_math=True)
            self.assertEqual(result["counts"]["gained"], 1)
            self.assertEqual(result["changes"][0]["after_prediction"], "12")

    def test_rescores_correct_and_incorrect_cases_using_final_region_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cases = root / "workers/baseline-worker0/cases/evaluation/gpqa"
            cases.mkdir(parents=True)
            for case_id, gold, text, old_prediction, old_correct in (
                ("recovered", "A", "**Final answer**: (A)", None, False),
                ("regression", "A", "Final answer: (A)\n**Final answer**: (B)", "A", True),
                ("open", "A", "", None, False),
            ):
                record = {
                    "task": "gpqa",
                    "id": case_id,
                    "gold": gold,
                    "answer_format": "choice",
                    "choices": ["A", "B", "C", "D"],
                    "conditions": {
                        "plain_ar": {
                            "answer_text": text,
                            "body_text": "Final answer: (A)",
                            "prediction": old_prediction,
                            "correct": old_correct,
                        }
                    },
                }
                (cases / f"{case_id}.json").write_text(json.dumps(record))
            before = {p: p.read_bytes() for p in cases.glob("*.json")}
            result = rescore.rescore_run(root)
            self.assertEqual(result["counts"]["total"], 3)
            self.assertEqual(result["counts"]["gained"], 1)
            self.assertEqual(result["counts"]["lost"], 1)
            self.assertEqual(result["counts"]["after_missing"], 1)
            self.assertEqual(before, {p: p.read_bytes() for p in cases.glob("*.json")})
            self.assertEqual(len(result["inputs"]), 3)

    def test_missing_saved_cases_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                rescore.rescore_run(folder)

    def test_math_cases_are_skipped_and_duplicates_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cases = root / "workers/worker0/cases/evaluation/math500"
            cases.mkdir(parents=True)
            record = {
                "task": "math500",
                "id": "one",
                "answer_format": "math",
                "conditions": {"plain_ar": {}},
            }
            (cases / "one.json").write_text(json.dumps(record))
            self.assertEqual(rescore.rescore_run(root)["counts"], {"skipped_math": 1})
            (cases / "duplicate.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                rescore.rescore_run(root)
