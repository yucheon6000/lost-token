import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.recurrent_memory import final_response, instruction
from test_recurrent_memory import ThinkingTokenizer


class MainControlTests(unittest.TestCase):
    def test_main_method_defaults_are_preserved(self):
        spec = load_spec()
        exp = spec["experiment"]
        self.assertTrue(exp["repetition_guard"]["enabled"])
        self.assertEqual(exp["selection"], "lookahead")
        self.assertEqual(exp["branch_tokens"], 64)
        self.assertEqual(
            exp["lookahead"],
            {
                "statistic": "mean_logprob",
                "margin": 0.1,
                "min_tokens": 16,
            },
        )
        self.assertIsNotNone(exp["memory_preamble"])
        self.assertIsNone(exp.get("budget_forcing"))
        self.assertEqual(exp["arms"], ["plain_ar", "filtered_futures"])
        self.assertEqual(spec["data"], {"prompt_limit": 32768, "shuffle_seed": 20260921})
        self.assertEqual(
            instruction({"answer_format": "math"}),
            "Please reason step by step, and put your final answer within \\boxed{}.\n\nProblem:\n",
        )

    def test_final_answer_scoring_uses_dataset_reference_first(self):
        from types import SimpleNamespace

        tokenizer = ThinkingTokenizer()
        model = SimpleNamespace(tokenizer=tokenizer, decode=tokenizer.decode, eos_ids={127})
        row = {"answer_format": "math", "gold": "2"}
        body = tokenizer.encode(r"work</think>\boxed{3}")
        with patch("lost_tokens.recurrent_memory.math_correct", return_value=False) as scorer:
            result = final_response(model, body, row, 126)
        scorer.assert_called_once_with("2", "3")
        self.assertEqual(result["prediction"], "3")
        self.assertFalse(result["correct"])
