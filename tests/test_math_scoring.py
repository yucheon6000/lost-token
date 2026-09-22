import unittest
from lost_tokens.math_scoring import boxed_answer, math_correct


class MathScoringTests(unittest.TestCase):
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
