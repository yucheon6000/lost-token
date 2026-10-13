"""Output, checkpoint and sampling parity for CPU overhead optimizations."""

import copy
import unittest
from unittest.mock import patch

import torch

from lost_tokens.core import RunStore, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, raw_text, run_condition
from lost_tokens.repetition import repeated_suffix
import test_knobs as knobs
import test_recurrent_memory as base


class ExactCPUOptimizationTests(unittest.TestCase):
    # Reuse fixtures without inheriting unrelated test cases.
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    setUp = base.RecurrentTests.setUp

    def tearDown(self):
        self.model.cfg.pop("exact_cpu_optimizations", None)

    def make_decoder(self, enabled):
        self.model.cfg["exact_cpu_optimizations"] = enabled
        return StreamDecoder(self.model, self.cfg["experiment"])

    def test_reseeded_generator_matches_fresh_generator_and_logits(self):
        original = self.make_decoder(False)
        optimized = self.make_decoder(True)
        state = original.prefill(self.model.encode("Test") + [1])
        optimized_state = copy.deepcopy(state)
        for seed in (1, 51, 2, 51, 3, 95021):
            expected = original.sample(state, seed)
            actual = optimized.sample(optimized_state, seed)
            self.assertEqual(expected, actual)
            original.advance(state, [expected[0]], generated=True)
            optimized.advance(optimized_state, [actual[0]], generated=True)
            self.assertTrue(torch.equal(state.logits, optimized_state.logits))

    def test_repetition_guard_matches_full_history_and_reuses_duplicate_checks(self):
        decoder = self.make_decoder(True)
        state = decoder.prefill([1, 65])
        for period in (1, 3, 32):
            for size in (0, 63, 64, 127, 128, 257):
                state.generated_ids = (
                    ([65 + i % period for i in range(300)])[-size:] if size else []
                )
                self.assertEqual(
                    decoder.loop_guard(state),
                    repeated_suffix(
                        state.generated_ids, self.cfg["experiment"]["repetition_guard"]
                    ),
                )
        state.generated_ids = [65] * 256
        decoder.loop_guard(state)
        before = decoder.cached_guard.cache_info().hits
        decoder.loop_guard(state)
        self.assertEqual(decoder.cached_guard.cache_info().hits, before + 1)

    def test_token_cache_preserves_special_tokens_and_is_bounded(self):
        self.model.cfg["exact_cpu_optimizations"] = True
        for ids in ([1, 65, 126, 127], [65] * 65, [], [0, 13, 10]):
            for skip in (False, True):
                self.assertEqual(
                    self.model.decode_tokens(ids, skip),
                    self.model.tokenizer.decode(ids, skip_special_tokens=skip),
                )
        self.assertEqual(raw_text(self.model, [1, 65, 126]), "<think>A</think>")
        before = self.model._decode_tail.cache_info().hits
        self.model.decode([65, 66])
        self.model.decode([65, 66])
        self.assertGreater(self.model._decode_tail.cache_info().hits, before)
        for i in range(300):
            self.model.decode([65, i // 128, i % 128])
        self.assertLessEqual(self.model._decode_tail.cache_info().currsize, 256)

    def test_plain_and_branching_conditions_preserve_all_nontiming_records(self):
        self.cfg["experiment"].update(max_output_tokens=24, min_branch_interval_tokens=4)
        for arm in ("plain_ar", "reference_only", "all_futures", "filtered_futures"):
            patches = [
                patch.object(StreamDecoder, "candidates", base.RecurrentTests.eligible),
                patch("lost_tokens.recurrent_memory.compare_rollouts", base.RecurrentTests.keep),
            ]
            with patches[0], patches[1]:
                self.model.cfg["exact_cpu_optimizations"] = False
                expected_store = RunStore(self.root / (arm + "-original"), {})
                expected = run_condition(
                    self.model, expected_store, self.row, self.cfg, "test", arm, lambda _: None
                )
                self.model.cfg["exact_cpu_optimizations"] = True
                actual_store = RunStore(self.root / (arm + "-optimized"), {})
                actual = run_condition(
                    self.model, actual_store, self.row, self.cfg, "test", arm, lambda _: None
                )
            self.assertEqual(
                knobs.fingerprint(expected, expected_store), knobs.fingerprint(actual, actual_store)
            )

    def test_optimized_forcing_and_interrupted_replay_match_original(self):
        self.cfg["experiment"].update(
            max_output_tokens=32,
            budget_forcing={"force_at_body_tokens": 20, "answer_tokens": 11},
        )
        self.model.cfg["exact_cpu_optimizations"] = False
        expected = run_condition(
            self.model,
            RunStore(self.root / "original", {}),
            self.row,
            self.cfg,
            "test",
            "plain_ar",
            lambda _: None,
        )
        self.model.cfg["exact_cpu_optimizations"] = True
        paused = PausableStore(self.root / "paused", {}, stop_after_calls=3)
        with self.assertRaises(RequestedPause):
            run_condition(
                self.model, paused, self.row, self.cfg, "test", "plain_ar", lambda _: None
            )
        hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
        actual = run_condition(
            self.model,
            RunStore(paused.path, {}, resume=True),
            self.row,
            self.cfg,
            "test",
            "plain_ar",
            lambda _: None,
        )
        self.assertEqual(knobs.strip_time(expected), knobs.strip_time(actual))
        self.assertTrue(
            all(
                file_digest(paused.path / "checkpoints" / name) == sha
                for name, sha in hashes.items()
            )
        )
