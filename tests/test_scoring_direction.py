"""The dataset answer must remain the reference in asymmetric math verification."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lost_tokens.recurrent_memory import final_response


class ScoringDirectionTests(unittest.TestCase):
    def test_math_verifier_receives_dataset_gold_before_extracted_prediction(self):
        model = SimpleNamespace(
            eos_ids={127},
            tokenizer=SimpleNamespace(decode=lambda *args, **kwargs: "</think>answer"),
            decode=lambda ids: "answer",
        )
        row = {"answer_format": "math", "gold": "dataset reference"}
        with (
            patch("lost_tokens.recurrent_memory.natural_answer", return_value="model prediction"),
            patch("lost_tokens.recurrent_memory.math_correct", return_value=False) as verify,
        ):
            result = final_response(model, [126, 65], row, 126)
        verify.assert_called_once_with("dataset reference", "model prediction")
        self.assertFalse(result["correct"])


if __name__ == "__main__":
    unittest.main()
