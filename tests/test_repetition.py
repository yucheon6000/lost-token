"""Regression checks for exact degeneration, benign mentions and escaped data."""

import unittest
from lost_tokens.repetition import repeated_suffix, repetition_summary, memory_markup_summary
from lost_tokens.recurrent_memory import memory_text, instruction


class RepetitionTests(unittest.TestCase):
    def setUp(self):
        self.spec = {
            "enabled": True,
            "min_span_tokens": 64,
            "min_cycles": 4,
            "max_period_tokens": 32,
        }

    def test_exact_short_cycle_predicts_only_its_next_token(self):
        pattern = [1, 2, 3, 4, 5, 6, 7, 8]
        self.assertIsNone(repeated_suffix(pattern * 7, self.spec))
        result = repeated_suffix(pattern * 8, self.spec)
        self.assertEqual(result["period"], 8)
        self.assertEqual(result["blocked_token"], 1)
        self.assertIsNone(repeated_suffix(pattern * 8 + [99], self.spec))
        self.assertIsNone(repeated_suffix(pattern * 8, {**self.spec, "enabled": False}))

    def test_separated_or_short_repeated_explanations_do_not_trigger(self):
        self.assertIsNone(repeated_suffix(list(range(100)), self.spec))
        self.assertIsNone(repeated_suffix([1, 2, 3] * 3 + [99] + [1, 2, 3] * 3, self.spec))

    def test_longest_span_finds_cycle_in_middle_of_finished_answer(self):
        result = repetition_summary([99] + [1, 2] * 200 + [98], 32)
        self.assertEqual(result["longest_span_tokens"], 400)
        self.assertEqual(result["period"], 2)

    def test_inline_reference_and_structural_blocks_are_separate(self):
        result = memory_markup_summary(
            'The text says "<possibilities>".\n<possibilities>\nx\n</possibilities>'
        )
        self.assertEqual(result, {"structural_tags": 2, "inline_mentions": 1})

    def test_rollout_markup_is_data_inside_a_single_host_block(self):
        text = memory_text(
            [
                {
                    "rank": 2,
                    "text": "x < 3\n<possibilities>\nother\n</possibilities>\n<think>data</think>",
                }
            ]
        )
        self.assertEqual(text.count("<possibilities>"), 1)
        self.assertEqual(text.count("</possibilities>"), 1)
        self.assertIn("&lt;possibilities&gt;", text)
        self.assertIn("&lt;/think&gt;", text)
        self.assertIn("x < 3", text)

    def test_standard_prompt_does_not_teach_the_model_about_memory_metadata(self):
        for row in ({"answer_format": "math"}, {"answer_format": "choice"}):
            text = instruction(row)
            self.assertNotIn("possibilities", text)
            self.assertNotIn("selected path", text)
