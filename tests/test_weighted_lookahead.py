"""Weighted selection preserves uniform memory scores and default replay behavior."""

import unittest

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore
from lost_tokens.recurrent_memory import (
    memory_quality_gate,
    rollout_statistic,
    select_rollout,
    validate_selection,
)
import test_knobs as knobs
import test_recurrent_memory as base
from test_lookahead import preview
import test_memory_quality as quality


class WeightedSelectionTests(unittest.TestCase):
    def exp(self, weights=None):
        exp = {
            "selection": "lookahead",
            "branch_tokens": 64,
            "lookahead": {"statistic": "mean_logprob", "margin": 0.1, "min_tokens": 1},
            "memory_quality_gate": {"max_score_gap": 0.1},
        }
        if weights is not None:
            exp["lookahead"]["half_weights"] = weights
        return exp

    def test_full_preview_splits_63_continuations_into_31_and_32(self):
        p = preview(1, [-100.0] + [-0.8] * 31 + [-0.2] * 32, ids=[65] * 64)
        self.assertAlmostEqual(rollout_statistic(p, "mean_logprob", [0.25, 0.75]), -0.35)
        self.assertAlmostEqual(rollout_statistic(p, "mean_logprob"), (-0.8 * 31 - 0.2 * 32) / 63)
        p["raw_log_probabilities"][0] = -0.001
        self.assertAlmostEqual(rollout_statistic(p, "mean_logprob", [0.25, 0.75]), -0.35)

    def test_empty_and_single_continuation_are_defined(self):
        self.assertIsNone(rollout_statistic(preview(1, [-0.1]), "mean_logprob", [0.25, 0.75]))
        self.assertEqual(
            rollout_statistic(preview(1, [-0.1, -0.4]), "mean_logprob", [0.25, 0.75]), -0.4
        )

    def test_late_advantage_can_change_selection_without_changing_memory_score(self):
        previews = [
            preview(1, [-0.1, -0.6, -0.6, -0.6, -0.6]),
            preview(2, [-9.0, -1.2, -1.2, -0.1, -0.1]),
        ]
        old = select_rollout(previews, self.exp(), {127})
        exp = self.exp([0.25, 0.75])
        result = select_rollout(previews, exp, {127})
        self.assertEqual(old["selected_rank"], 1)
        self.assertEqual(result["selected_rank"], 2)
        self.assertEqual(result["half_weights"], [0.25, 0.75])
        self.assertAlmostEqual(result["scores"][1]["value"], -0.375)
        gate = memory_quality_gate(previews, result, exp)
        self.assertAlmostEqual(gate["scores"][1]["value"], -0.65)
        self.assertAlmostEqual(gate["scores"][0]["value"], -0.6)
        self.assertEqual(gate["retained_ranks"], [1])

    def test_easy_opening_alone_no_longer_causes_a_flip(self):
        previews = [
            preview(1, [-0.1, -0.6, -0.6, -0.6, -0.6]),
            preview(2, [-0.1, -0.1, -0.1, -0.8, -0.8]),
        ]
        self.assertEqual(select_rollout(previews, self.exp(), {127})["selected_rank"], 2)
        self.assertEqual(
            select_rollout(previews, self.exp([0.25, 0.75]), {127})["selected_rank"], 1
        )

    def test_terminal_and_short_candidates_remain_ineligible(self):
        for p in (preview(2, [-0.1, -0.01], stop_marker="</think>"), preview(2, [-0.1])):
            result = select_rollout([preview(1, [-0.1, -1.0]), p], self.exp([0.25, 0.75]), {127})
            self.assertEqual(result["selected_rank"], 1)
            self.assertFalse(result["scores"][1]["eligible"])

    def test_invalid_weights_are_rejected_and_old_config_stays_valid(self):
        for value in (
            None,
            [],
            [1],
            [1, 0, 0],
            [True, 0],
            ["0.25", 0.75],
            [-0.25, 1.25],
            [0, 0],
            [0.25, 0.25],
            [float("nan"), 0.75],
            [float("inf"), 0],
        ):
            exp = self.exp()
            exp["lookahead"]["half_weights"] = value
            with self.subTest(weights=value), self.assertRaises(ValueError):
                validate_selection(exp)
        validate_selection(self.exp())
        validate_selection(self.exp([0.25, 0.75]))

    def test_config_only_adds_weights_to_the_selfcorrect_method(self):
        current = load_spec("configs/vllm-ours-weighted.json")
        self.assertEqual(current["experiment"]["lookahead"].pop("half_weights"), [0.25, 0.75])
        self.assertEqual(current, load_spec("configs/vllm-ours-selfcorrect.json"))


class WeightedProtocolTests(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    eligible = staticmethod(base.RecurrentTests.eligible)
    patches = quality.MemoryQualityProtocol.patches
    run_with = quality.MemoryQualityProtocol.run_with
    audited = knobs.KnobTests.audited

    def setUp(self):
        quality.MemoryQualityProtocol.setUp(self)
        self.cfg["experiment"].update(branch_tokens=4, max_output_tokens=16)
        self.cfg["experiment"]["lookahead"]["half_weights"] = [0.25, 0.75]

    def test_weighted_selection_and_uniform_memory_are_audited(self):
        reviewed, result = self.audited("filtered_futures", self.patches())
        self.assertEqual(reviewed["completed_conditions"], 1)
        for event in result["events"]:
            self.assertEqual(event["selection"]["half_weights"], [0.25, 0.75])
            chosen = next(p for p in event["previews"] if p["rank"] == event["selected_rank"])
            self.assertEqual(event["committed_ids"], chosen["ids"])

    def test_resume_reuses_all_saved_weighted_decisions(self):
        expected = self.run_with(RunStore(self.root / "expected", {}))
        from lost_tokens.protocol import PausableStore, RequestedPause

        for stop in (5, 12, 20):
            store = PausableStore(self.root / f"paused-{stop}", {}, stop_after_calls=stop)
            try:
                self.run_with(store)
            except RequestedPause:
                pass
            actual = self.run_with(RunStore(store.path, {}, resume=True))
            self.assertEqual(knobs.strip_time(expected), knobs.strip_time(actual))
