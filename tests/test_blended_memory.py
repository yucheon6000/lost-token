"""Similarity can rescue a low-confidence memory without changing the chosen rollout."""

import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.recurrent_memory import StreamDecoder, memory_quality_gate, select_rollout
from test_lookahead import preview
import test_memory_quality as quality


class BlendedMemoryTests(unittest.TestCase):
    def test_gap_allowance_is_highest_at_center_and_keeps_basic_eligibility(self):
        exp = quality.MemoryQualityDecisions().exp()
        exp["memory_quality_gate"]["similarity_gap_bonus"] = 0.05
        previews = [
            preview(1, [-0.1, -0.325]),
            preview(2, [-0.1, -0.474]),
            preview(3, [-0.1, -0.33], stop_marker="</think>"),
        ]
        selection = select_rollout(previews, exp, {127})
        self.assertEqual(memory_quality_gate(previews, selection, exp)["retained_ranks"], [2])
        for cosine, retained in ((0.2, []), (0.525, [2]), (0.84, [])):
            with self.subTest(cosine=cosine):
                similarity = {
                    "ranks": [1, 2],
                    "similarity_matrix": [[1.0, cosine], [cosine, 1.0]],
                    "min_threshold": 0.2,
                    "threshold": 0.85,
                }
                result = memory_quality_gate(previews, selection, exp, similarity)
                self.assertEqual(result["retained_ranks"], retained)

    def test_blended_config_changes_only_memory_gate(self):
        cfg = load_spec("configs/vllm-ours-blended-memory.json")
        bonus = cfg["experiment"]["memory_quality_gate"].pop("similarity_gap_bonus")
        self.assertEqual(bonus, 0.05)
        self.assertEqual(cfg, load_spec("configs/vllm-ours-weighted.json"))


class BlendedMemoryAuditTests(unittest.TestCase):
    setUpClass = quality.MemoryQualityProtocol.setUpClass.__func__
    setUpClass = classmethod(setUpClass)
    audited = quality.MemoryQualityProtocol.audited

    def setUp(self):
        quality.MemoryQualityProtocol.setUp(self)
        self.cfg["experiment"]["memory_quality_gate"]["similarity_gap_bonus"] = 0.05
        self.cfg["similarity"].update(min_threshold=0.2, threshold=0.85)

    def test_native_audit_checks_rescued_memory_and_exact_commit(self):
        class Encoder:
            def encode(self, texts):
                vectors = [
                    [1.0, 0.0] if t.startswith("A") else [0.525, 0.8511022265] for t in texts
                ]
                return vectors, sum(map(len, texts))

        def candidates(decoder, state):
            result = quality.MemoryQualityProtocol.eligible(decoder, state)
            result["items"] = result["items"][:2]
            return result

        def sample(decoder, state, seed):
            return 68, -0.34 if 66 in state.generated_ids else -0.2

        patches = [
            patch.object(StreamDecoder, "candidates", candidates),
            patch.object(StreamDecoder, "sample", sample),
            patch.object(self.model, "semantic_encoder", Encoder()),
        ]
        report, result = self.audited("filtered_futures", patches)
        self.assertEqual(report["completed_conditions"], 1)
        injected = [event for event in result["events"] if event["retained_ranks"]]
        self.assertTrue(injected)
        for event in injected:
            score = event["memory_quality"]["scores"][1]
            self.assertGreater(score["gap"], 0.1)
            self.assertLessEqual(score["gap"], score["allowed_score_gap"])
            self.assertEqual(event["retained_ranks"], [2])
            self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
