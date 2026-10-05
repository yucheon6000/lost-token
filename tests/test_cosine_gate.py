"""Numerical cosine, complete pairwise deduplication, and empty-input behavior."""

import math
from types import SimpleNamespace
import unittest
import torch

from lost_tokens.cosine import CosineEncoder, compare_rollouts, cosine_matrix, select_distinct
from lost_tokens.recurrent_memory import memory_text


class CosineTests(unittest.TestCase):
    def test_actual_cosine_invariant_to_vector_scale(self):
        self.assertEqual(
            cosine_matrix([[2.0, 0.0], [3.0, 0.0], [0.0, 4.0], [-2.0, 0.0]]),
            [
                [1.0, 1.0, 0.0, -1.0],
                [1.0, 1.0, 0.0, -1.0],
                [0.0, 0.0, 1.0, 0.0],
                [-1.0, -1.0, 0.0, 1.0],
            ],
        )

    def test_compares_alternatives_with_other_retained_alternatives(self):
        matrix = cosine_matrix([[1.0, 0.0], [0.0, 1.0], [0.0, 2.0]])
        ranks, decisions = select_distinct([1, 2, 3], matrix, [True] * 3, 0.9)
        self.assertEqual(ranks, [2])
        self.assertEqual(decisions[1]["compared_ranks"], [1, 2])
        self.assertEqual(decisions[1]["closest_rank"], 2)
        self.assertTrue(decisions[1]["drop_alternative"])

    def test_threshold_boundary_and_empty_reference(self):
        self.assertEqual(
            select_distinct([1, 2], [[1.0, 0.9], [0.9, 1.0]], [True, True], 0.9)[0], []
        )
        self.assertEqual(
            select_distinct([1, 2], [[1.0, 0.899], [0.899, 1.0]], [True, True], 0.9)[0], [2]
        )
        self.assertEqual(
            select_distinct([1, 2], [[None, None], [None, 1.0]], [False, True], 0.9)[0], []
        )

    def test_blank_fragments_are_not_treated_as_distinct(self):
        class NeverEncode:
            def encode(self, texts):
                raise AssertionError("No valid text should be encoded")

        result = compare_rollouts(
            NeverEncode(), [{"rank": 1, "text": " "}, {"rank": 2, "text": "\n"}], 0.9
        )
        self.assertEqual(result["retained_ranks"], [])
        self.assertEqual(result["embedding_cost"]["texts"], 0)

    def test_invalid_vectors_rejected(self):
        for vectors in ([], [[0.0, 0.0]], [[math.nan, 1.0]]):
            with self.assertRaises(ValueError):
                cosine_matrix(vectors)

    def test_last_real_token_pooling_and_normalization(self):
        encoder = CosineEncoder.__new__(CosineEncoder)
        encoder.torch = torch
        encoder.cfg = {"max_tokens": 2, "batch_size": 8, "device": "cpu"}
        encoder.tokenizer = lambda texts, **kwargs: {
            "input_ids": torch.tensor([[0, 1], [2, 3]]),
            "attention_mask": torch.tensor([[0, 1], [1, 1]]),
        }
        encoder.model = lambda **kwargs: SimpleNamespace(
            last_hidden_state=torch.tensor([[[999.0, 0.0], [0.0, 2.0]], [[9.0, 9.0], [3.0, 4.0]]])
        )
        vectors, count = encoder.encode(["first", "second"])
        self.assertTrue(
            torch.allclose(torch.tensor(vectors), torch.tensor([[0.0, 1.0], [0.6, 0.8]]))
        )
        self.assertEqual(count, 3)
        with self.assertRaises(ValueError):
            encoder.encode([" "])
        encoder.cfg["max_tokens"] = 1
        with self.assertRaises(ValueError):
            encoder.encode(["first", "second"])

    def test_memory_has_only_payload_and_delimiters(self):
        self.assertEqual(
            memory_text(
                [{"rank": 2, "text": " alternative A"}, {"rank": 3, "text": "alternative B"}]
            ),
            "\n<possibilities>\n- Alternative Path [1]: alternative A\n- Alternative Path [2]: alternative B\n</possibilities>\n",
        )
