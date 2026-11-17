import unittest

from lost_tokens.consensus import answer_consensus


class ConsensusTests(unittest.TestCase):
    def test_equivalent_math_answers_vote_together_without_a_reference(self):
        result = answer_consensus([r"\frac{1}{2}", "3", "0.5", None, r"\dfrac{2}{4}"], "math")
        self.assertEqual(result["prediction"], r"\frac{1}{2}")
        self.assertEqual(result["groups"][0]["members"], [0, 2, 4])
        self.assertTrue(result["strict_majority"])
        self.assertEqual(result["abstentions"], [3])

    def test_choice_tie_is_frozen_member_order_not_answer_letter(self):
        result = answer_consensus(["D", "A", "A", "D", None], "choice", "ABCD")
        self.assertEqual(result["prediction"], "D")
        self.assertTrue(result["tied"])
        self.assertFalse(result["strict_majority"])
        self.assertEqual(result["selected_member"], 0)

    def test_invalid_or_missing_choices_abstain_without_shrinking_denominator(self):
        result = answer_consensus([None, "Apple", "Z", "B", "B"], "choice", "ABCD")
        self.assertEqual(result["prediction"], "B")
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["requested_members"], 5)
        self.assertEqual(result["valid_members"], 2)
        self.assertFalse(result["strict_majority"])

    def test_all_missing_is_missing_instead_of_inventing_an_answer(self):
        result = answer_consensus([None, "", " "], "math")
        self.assertIsNone(result["prediction"])
        self.assertIsNone(result["selected_member"])
        self.assertEqual(result["support"], 0)

    def test_consensus_never_returns_an_answer_absent_from_members(self):
        predictions = ["4", "5", "6", "7", "8"]
        result = answer_consensus(predictions, "math")
        self.assertIn(result["prediction"], predictions)
        self.assertEqual(result["prediction"], "4")

    def test_invalid_format_and_empty_roster_are_rejected(self):
        for predictions, fmt in (([], "choice"), (["A"], "unknown")):
            with self.assertRaises(ValueError):
                answer_consensus(predictions, fmt, "ABCD")
