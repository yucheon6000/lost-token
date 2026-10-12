"""Entropy gates, sentence boundaries, and budget forcing compose and replay exactly."""

import copy
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import torch

from lost_tokens.audit import audit
from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, atomic_json, digest, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, rollout_boundary, run_condition
import test_recurrent_memory as base
import test_knobs as knobs


class ThreeFeatureTests(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    setUp = base.RecurrentTests.setUp
    eligible = staticmethod(base.RecurrentTests.eligible)
    keep = staticmethod(base.RecurrentTests.keep)
    audited = knobs.KnobTests.audited

    POLICY = {"min_tokens": 13, "patterns": [".\n", ".\t", ". ", "\n\n", "\n-", "\n*"]}

    def configure(self):
        self.cfg["experiment"].update(
            max_output_tokens=32,
            branch_tokens=16,
            min_branch_entropy=0.65,
            rollout_early_stop=copy.deepcopy(self.POLICY),
            budget_forcing={"force_at_body_tokens": 17, "answer_tokens": 14},
        )

    @staticmethod
    def answer_sample(decoder, state, seed):
        if 126 in state.generated_ids:
            answer = list(map(ord, "\\boxed{2}")) + [127]
            offset = len(state.generated_ids) - state.generated_ids.index(126) - 1
            return answer[min(offset, len(answer) - 1)], -1.0
        return 10, -1.0

    def controlled(self, store, arm="all_futures"):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", self.answer_sample),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            return run_condition(self.model, store, self.row, self.cfg, "test", arm, lambda _: None)

    def logits(self, probabilities):
        root = self.decoder.prefill([65])
        root.logits = torch.full((128,), -torch.inf)
        for token, probability in probabilities:
            root.logits[token] = torch.log(torch.tensor(probability))
        return root

    def test_entropy_gate_excludes_low_entropy_with_two_qualifying_candidates(self):
        self.cfg["experiment"].update(min_candidate_probability=0.2, min_branch_entropy=0.65)
        root = self.logits([(65, 0.79), (66, 0.21)])
        result = self.decoder.candidates(root)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["items"], [])
        self.assertLess(result["entropy"], 0.65)
        self.cfg["experiment"]["min_branch_entropy"] = None
        self.assertTrue(self.decoder.candidates(root)["eligible"])

    def test_entropy_gate_preserves_all_qualifying_candidates(self):
        self.cfg["experiment"]["min_branch_entropy"] = 0.65
        result = self.decoder.candidates(self.logits([(65, 0.4), (66, 0.35), (43, 0.25)]))
        self.assertTrue(result["eligible"])
        self.assertEqual([i["token_id"] for i in result["items"]], [65, 66, 43])

    def test_numeric_tokens_do_not_bypass_entropy_gate(self):
        self.cfg["experiment"].update(min_candidate_probability=0.2, min_branch_entropy=0.65)
        self.assertFalse(self.decoder.candidates(self.logits([(49, 0.79), (50, 0.21)]))["eligible"])

    def test_choice_tasks_keep_the_same_branching_policy(self):
        self.configure()
        self.row.update(answer_format="choice", gold="A")
        result = self.controlled(RunStore(self.root / "choice", {}))
        self.assertEqual(len(result["events"]), 2)
        self.assertTrue(all(e["memory_ids"] for e in result["events"]))

    def test_entropy_threshold_is_inclusive_and_special_tokens_still_block_forks(self):
        root = self.logits([(65, 0.5), (66, 0.5)])
        entropy = self.decoder.candidates(root)["entropy"]
        self.cfg["experiment"]["min_branch_entropy"] = entropy
        self.assertTrue(self.decoder.candidates(root)["eligible"])
        self.cfg["experiment"]["min_branch_entropy"] = entropy + 1e-5
        self.assertFalse(self.decoder.candidates(root)["eligible"])
        self.cfg["experiment"]["min_branch_entropy"] = 0
        self.assertFalse(
            self.decoder.candidates(self.logits([(126, 0.4), (65, 0.3), (66, 0.3)]))["eligible"]
        )
        self.assertFalse(self.decoder.candidates(self.logits([(65, 1.0)]))["eligible"])

    def rollout(self, text, count=32):
        self.cfg["experiment"].update(branch_tokens=count, rollout_early_stop=self.POLICY)
        ids = self.model.encode(text)
        remaining = iter(ids[1:] + [ord("x")] * count)
        root = self.decoder.prefill([1, 65])
        with patch.object(StreamDecoder, "sample", lambda *_: (next(remaining), -1.0)):
            return self.decoder.rollout(root, ids[0], 12)

    def test_every_boundary_stops_rollout_when_split_across_tokens(self):
        for pattern in self.POLICY["patterns"]:
            text = "a" * 12 + pattern
            with self.subTest(pattern=repr(pattern)):
                result = self.rollout(text + "NEVER_GENERATE")
                self.assertEqual(result["ids"], self.model.encode(text))
                self.assertEqual(result["cost"]["output_tokens"], len(text))

    def test_boundary_within_one_token_also_stops_rollout(self):
        decode = self.model.decode
        with patch.object(self.model, "decode", lambda ids: decode(ids).replace("Z", ".\n")):
            result = self.rollout("a" * 12 + "Z" + "NEVER_GENERATE")
        self.assertEqual(len(result["ids"]), 13)

    def test_early_boundary_before_minimum_is_not_reused_later(self):
        result = self.rollout(". " + "a" * 30)
        self.assertEqual(len(result["ids"]), 32)
        self.assertIsNone(rollout_boundary(self.model, [], self.POLICY))

    def test_single_newline_and_backslash_do_not_stop_rollouts(self):
        for suffix in ("\n", "\\", "\\\\", "\\n", "."):
            with self.subTest(suffix=repr(suffix)):
                self.assertEqual(len(self.rollout("a" * 12 + suffix)["ids"]), 32)

    def test_rollout_cap_can_precede_minimum_and_eos_still_terminates(self):
        self.assertEqual(len(self.rollout("a" * 32, count=5)["ids"]), 5)
        result = self.rollout("abc" + chr(127))
        self.assertEqual(result["ids"], [97, 98, 99, 127])

    def test_boundary_policy_does_not_stop_main_body(self):
        self.cfg["experiment"].update(max_output_tokens=20, rollout_early_stop=self.POLICY)
        root = self.decoder.prefill([1, 65])
        with patch.object(StreamDecoder, "sample", lambda *_: (10, -1.0)):
            result = self.decoder.segment(root, 20, 1, 0, False)
        self.assertEqual(len(result["ids"]), 20)

    def test_all_arms_hit_forcing_boundary_without_rollout_overshoot(self):
        self.configure()
        for arm in ("plain_ar", "reference_only", "all_futures", "filtered_futures"):
            with self.subTest(arm=arm):
                result = self.controlled(RunStore(self.root / arm, {}), arm)
                self.assertEqual(result["forced_think_end_at"], 17)
                self.assertEqual(result["body_ids"][17], 126)
                self.assertLessEqual(len(result["body_ids"]), 32)
                self.assertTrue(result["ended"])
                self.assertTrue(result["correct"])
                self.assertTrue(all(e["body_position"] < 17 for e in result["events"]))
                for event in result["events"]:
                    self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
                    self.assertLessEqual(event["body_position"] + len(event["committed_ids"]), 17)
                if result["events"]:
                    self.assertEqual(len(result["events"][0]["committed_ids"]), 13)
                    self.assertEqual(len(result["events"][-1]["committed_ids"]), 3)

    def test_zero_answer_reservation_still_closes_thinking_for_scanning_arm(self):
        self.configure()
        self.cfg["experiment"]["budget_forcing"]["answer_tokens"] = 0
        result = self.controlled(RunStore(self.root / "zero-answer", {}))
        self.assertEqual(len(result["body_ids"]), 18)
        self.assertTrue(result["thinking_complete"])
        self.assertIsNone(result["prediction"])

    def test_natural_thinking_end_in_selected_rollout_suppresses_forcing(self):
        self.configure()

        def sample(decoder, state, seed):
            return (126, -1.0) if state.ids[-1] == 65 else self.answer_sample(decoder, state, seed)

        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", sample),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "natural", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertIsNone(result["forced_think_end_at"])
        self.assertEqual(len(result["events"]), 1)
        self.assertTrue(result["correct"])

    def test_final_answer_mask_blocks_native_opening_and_refills_top_k(self):
        self.cfg["experiment"]["top_k"] = 2
        root = self.logits([(1, 0.8), (65, 0.12), (127, 0.08)])
        self.decoder.final_answer_only = True
        logits = self.decoder.answer_logits(root, root.logits)
        self.assertTrue(torch.isneginf(logits[1]))
        self.assertEqual(set(logits.topk(2).indices.tolist()), {65, 127})
        for seed in range(10):
            self.assertIn(self.decoder.sample(root, seed)[0], {65, 127})

    def test_final_answer_mask_blocks_split_text_reasoning_marker(self):
        root = self.logits([(62, 0.9), (65, 0.05), (127, 0.05)])
        for prefix in ("<reasoning", "<think"):
            with self.subTest(prefix=prefix):
                root.ids = self.model.encode("</think> Final answer: " + prefix)
                self.decoder.final_answer_only = True
                logits = self.decoder.answer_logits(root, root.logits)
                self.assertTrue(torch.isneginf(logits[62]))
                self.assertFalse(torch.isneginf(logits[127]))

    def test_unbounded_original_sampling_still_allows_native_reasoning_token(self):
        root = self.logits([(1, 1.0)])
        self.assertFalse(self.decoder.final_answer_only)
        self.assertEqual(self.decoder.sample(root, 4)[0], 1)

    def test_final_answer_mask_allows_close_marker_and_rejects_no_valid_token(self):
        root = self.logits([(126, 0.6), (127, 0.4)])
        self.decoder.final_answer_only = True
        self.assertIn(self.decoder.sample(root, 4)[0], {126, 127})
        root.logits = torch.full((128,), -torch.inf)
        root.logits[1] = 0
        with self.assertRaisesRegex(ValueError, "No valid final-answer token"):
            self.decoder.sample(root, 4)

    def test_final_answer_mask_after_natural_and_forced_close_is_restored_on_resume(self):
        self.configure()
        original_sample = StreamDecoder.sample

        natural_close = False

        def attempts_reopening(decoder, state, seed):
            state.logits = torch.full((128,), -torch.inf)
            next_token, _ = self.answer_sample(decoder, state, seed)
            if natural_close and len(state.generated_ids) == 2:
                next_token = 126
            state.logits[next_token] = -2.0
            if 126 in state.generated_ids:
                state.logits[1] = 0.0
            return original_sample(decoder, state, seed)

        def run(store):
            with patch.object(StreamDecoder, "sample", attempts_reopening):
                return run_condition(
                    self.model, store, self.row, self.cfg, "test", "plain_ar", lambda _: None
                )

        for natural_close in (False, True):
            with self.subTest(natural_close=natural_close):
                prefix = f"mask-{natural_close}"
                expected = run(RunStore(self.root / f"{prefix}-expected", {}))
                self.assertTrue(expected["correct"])
                self.assertNotIn(1, expected["body_ids"])
                self.assertEqual(expected["forced_think_end_at"], None if natural_close else 17)
                for stop in (3, 4, 5):
                    paused = PausableStore(
                        self.root / f"{prefix}-resume-{stop}", {}, stop_after_calls=stop
                    )
                    with self.assertRaises(RequestedPause):
                        run(paused)
                    actual = run(RunStore(paused.path, {}, resume=True))
                    self.assertEqual(knobs.strip_time(actual), knobs.strip_time(expected))

    def test_audit_rejects_native_reasoning_reopening_after_forcing(self):
        self.configure()

        def reopen(decoder, state, seed):
            if 126 in state.generated_ids and state.generated_ids[-1] == 126:
                return 1, -1.0
            return self.answer_sample(decoder, state, seed)

        with self.assertRaisesRegex(AssertionError, "Reasoning reopened"):
            self.audited("plain_ar", [patch.object(StreamDecoder, "sample", reopen)])

    def test_combined_method_resumes_at_rollout_commit_and_force_checkpoints(self):
        self.configure()
        expected = self.controlled(RunStore(self.root / "expected", {}), "filtered_futures")
        for stop in (3, 7, 10, 14, 17, 20):
            with self.subTest(stop=stop):
                paused = PausableStore(self.root / f"resume-{stop}", {}, stop_after_calls=stop)
                with self.assertRaises(RequestedPause):
                    self.controlled(paused, "filtered_futures")
                hashes = {
                    p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")
                }
                resumed = RunStore(paused.path, {}, resume=True)
                actual = self.controlled(resumed, "filtered_futures")
                self.assertEqual(knobs.strip_time(actual), knobs.strip_time(expected))
                self.assertGreater(resumed.hits, 0)
                self.assertTrue(
                    all(
                        file_digest(paused.path / "checkpoints" / n) == sha
                        for n, sha in hashes.items()
                    )
                )

    def test_audit_reconstructs_all_three_features(self):
        self.configure()
        for arm in ("plain_ar", "reference_only", "all_futures"):
            with self.subTest(arm=arm):
                reviewed, result = self.audited(
                    arm,
                    [
                        patch.object(StreamDecoder, "candidates", self.eligible),
                        patch.object(StreamDecoder, "sample", self.answer_sample),
                    ],
                )
                self.assertEqual(reviewed["completed_conditions"], 1)
                self.assertEqual(result["forced_think_end_at"], 17)

    def test_audit_rejects_fork_entropy_below_threshold(self):
        self.configure()
        self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.answer_sample),
            ],
        )
        run = self.root / "audit-all_futures"
        for path in (run / "checkpoints").glob("*.json"):
            saved = json.loads(path.read_text())
            out = saved["payload"]["result"]
            if saved["payload"]["label"].endswith("/scan") and out["fork"]:
                out["fork"]["entropy"] = 0.1
                out["checks"][-1]["entropy"] = 0.1
                saved["sha256"] = digest(saved["payload"])
                atomic_json(path, saved)
                break
        with self.assertRaises(AssertionError):
            audit(run, partial=True, model=self.model)

    def test_filtered_method_audit_uses_original_cosine_filter_and_memory(self):
        self.configure()
        encoder = SimpleNamespace(
            encode=lambda texts: (
                [[float(t.startswith(c)) for c in ("A", "B", "C")] for t in texts],
                sum(len(self.model.encode(t)) for t in texts),
            )
        )
        reviewed, result = self.audited(
            "filtered_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.answer_sample),
                patch.object(self.model, "semantic_encoder", encoder),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertTrue(result["correct"])
        self.assertEqual(result["events"][0]["retained_ranks"], [2, 3])
        self.assertNotIn("Variables:", result["events"][0]["memory_text"])

    def test_audit_rejects_short_rollout_without_a_stop_condition(self):
        self.configure()
        original = StreamDecoder.rollout

        def truncate(decoder, root, first, seed, count):
            out = original(decoder, root, first, seed, count)
            if count > 7:
                out["ids"] = out["ids"][:7]
                out["raw_log_probabilities"] = out["raw_log_probabilities"][:7]
                out["text"] = self.model.decode(out["ids"])
                out["cost"] = decoder.cost(len(root.ids), 7, 7)
            return out

        with self.assertRaises(AssertionError):
            self.audited(
                "all_futures",
                [
                    patch.object(StreamDecoder, "candidates", self.eligible),
                    patch.object(StreamDecoder, "sample", self.answer_sample),
                    patch.object(StreamDecoder, "rollout", truncate),
                ],
            )

    def test_method_config_differs_from_main_defaults_only_in_three_features(self):
        spec = load_spec(
            Path(__file__).resolve().parents[1] / "configs/bounded-entropy-sentence.json"
        )
        exp = spec["experiment"]
        self.assertEqual(
            exp["budget_forcing"]["force_at_body_tokens"]
            + 1
            + exp["budget_forcing"]["answer_tokens"],
            32768,
        )
        for key in ("budget_forcing", "min_branch_entropy", "rollout_early_stop"):
            self.assertIsNotNone(exp.pop(key))
        self.assertEqual(spec, load_spec())

    def test_config_rejects_malformed_entropy_and_boundary_controls(self):
        bad = [
            ("min_branch_entropy", -0.1),
            ("min_branch_entropy", True),
            ("min_branch_entropy", float("nan")),
            ("min_branch_entropy", float("inf")),
            ("min_branch_entropy", "0.65"),
            ("rollout_early_stop", True),
            ("rollout_early_stop", {"min_tokens": 13}),
            ("rollout_early_stop", {**self.POLICY, "min_tokens": 0}),
            ("rollout_early_stop", {**self.POLICY, "min_tokens": True}),
            ("rollout_early_stop", {**self.POLICY, "min_tokens": 33}),
            ("rollout_early_stop", {**self.POLICY, "patterns": []}),
            ("rollout_early_stop", {**self.POLICY, "patterns": "\n"}),
            ("rollout_early_stop", {**self.POLICY, "patterns": [""]}),
            ("rollout_early_stop", {**self.POLICY, "patterns": [13]}),
        ]
        for key, value in bad:
            with self.subTest(key=key, value=repr(value)):
                spec = load_spec()
                spec["experiment"][key] = value
                path = self.root / "bad.json"
                path.write_text(json.dumps(spec))
                with self.assertRaises(ValueError):
                    load_spec(path)


if __name__ == "__main__":
    unittest.main()
