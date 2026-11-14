import unittest
from concurrent.futures import ThreadPoolExecutor
from lost_tokens.math_scoring import boxed_answer, math_correct, natural_answer


class MathScoringTests(unittest.TestCase):
    def test_completed_math_answers_can_be_scored_from_case_threads(self):
        cases = [(r"\frac{1}{2}", "0.5"), ("2", "3"), ("12", "12"), ("2", None)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda pair: math_correct(*pair), cases))
        self.assertEqual(results, [True, False, True, False])

    def test_grade_ordinals_are_normalized_only_for_grade_questions(self):
        row = {"answer_format": "math", "question": "For which grade is the count closest?"}
        for answer in (r"12^{\text{th}}", r"12^{\mathrm{th}}", "12th"):
            self.assertEqual(natural_answer(r"\boxed{" + answer + "}", row), "12")
        for answer in (r"12^{th}", r"12^{\text{st}}", r"12^2", "12th + 1"):
            self.assertEqual(natural_answer(r"\boxed{" + answer + "}", row), answer)
        row["question"] = "Compute the exponent."
        self.assertEqual(natural_answer(r"\boxed{12^{\text{th}}}", row), r"12^{\text{th}}")

    def test_nested_and_escaped_braces(self):
        for value in (r"\frac{1}{2}", r"\{1,2\}", r"\sqrt{\frac{2}{3}}"):
            self.assertEqual(boxed_answer(r"work \boxed{" + value + "} end"), value)

    def test_missing_empty_and_unfinished_last_box(self):
        for text in (
            "",
            "42",
            r"\boxed{}",
            r"\boxed{ }",
            r"\boxed{\frac{1}{2}",
            r"\boxed{3} then \boxed{4",
        ):
            self.assertIsNone(boxed_answer(text))
        self.assertEqual(boxed_answer(r"\boxed{3} correction \boxed{4}"), "4")

    def test_standard_equivalence_and_failure(self):
        for gold, pred in ((r"\frac{1}{2}", "0.5"), ("2", r"\sqrt{4}"), (r"\{1,2\}", r"\{2,1\}")):
            self.assertTrue(math_correct(gold, pred))
        self.assertFalse(math_correct("2", "3"))
        self.assertFalse(math_correct("2", None))
        self.assertFalse(math_correct("2", "nonsense"))
