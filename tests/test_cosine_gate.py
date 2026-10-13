"""Numerical cosine, complete pairwise deduplication, and empty-input behavior."""

import math
from types import SimpleNamespace
import unittest
import torch

from lost_tokens.cosine import (
    CosineEncoder,
    compare_rollouts,
    cosine_matrix,
    select_distinct,
    recent_alternatives,
    select_recent_distinct,
)
from lost_tokens.recurrent_memory import memory_text


class CosineTests(unittest.TestCase):
    def test_recent_vectors_are_reused_without_encoding_history(self):
        calls = []

        class Encoder:
            def encode(self, texts):
                calls.append(texts)
                return [[1.0, 0.0], [0.0, 1.0]], 8

        recent = [{"event": 3, "rank": 2, "embedding": [0.0, 2.0]}]
        result = compare_rollouts(
            Encoder(),
            [{"rank": 1, "text": "Original."}, {"rank": 2, "text": "Alternative."}],
            0.85,
            recent=recent,
        )
        self.assertEqual(calls, [["Original.", "Alternative."]])
        self.assertEqual(result["embedding_cost"]["texts"], 2)
        self.assertEqual(result["retained_ranks"], [])
        decision = result["recent_decisions"][0]
        self.assertTrue(decision["drop_alternative"])
        self.assertEqual(decision["closest_alternative"], {"event": 3, "rank": 2})
        self.assertEqual(decision["max_cosine"], 1.0)

    def test_novel_alternative_and_empty_recent_window_are_retained(self):
        for recent in ([], [{"event": 0, "rank": 2, "embedding": [1.0, 0.0]}]):
            ranks, decisions = select_recent_distinct(
                [1, 2], [[1.0, 0.0], [0.0, 1.0]], [2], recent, 0.85
            )
            self.assertEqual(ranks, [2])
            self.assertFalse(decisions[0]["drop_alternative"])
        self.assertEqual(select_recent_distinct([1, 2], [None, None], [], [], 0.85), ([], []))

    def test_recent_threshold_is_inclusive(self):
        vector = [0.85, math.sqrt(1 - 0.85**2)]
        score = cosine_matrix([[1.0, 0.0], vector])[0][1]
        recent = [{"event": 0, "rank": 2, "embedding": [1.0, 0.0]}]
        self.assertEqual(
            select_recent_distinct([1, 2], [[0, 1], vector], [2], recent, score)[0], []
        )
        self.assertEqual(
            select_recent_distinct([1, 2], [[0, 1], vector], [2], recent, score + 1e-5)[0], [2]
        )

    def test_window_contains_only_newest_active_retained_alternatives(self):
        events = [
            {
                "index": i,
                "retained_ranks": [2],
                "similarity": {
                    "ranks": [1, 2],
                    "embeddings": [[1.0, 0.0], [0.0, 1.0]],
                },
            }
            for i in range(6)
        ]
        recent = recent_alternatives(events, [0, 2, 3, 4, 5], 4)
        self.assertEqual([r["event"] for r in recent], [2, 3, 4, 5])
        self.assertEqual(recent_alternatives(events, [], 4), [])
        self.assertEqual(recent_alternatives(events, [0], 0), [])
        events[-1]["retained_ranks"] = []
        self.assertEqual([r["event"] for r in recent_alternatives(events, [0, 5], 4)], [0])

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
            "\n<possibilities>\n alternative A\n\nalternative B\n</possibilities>\n",
        )
