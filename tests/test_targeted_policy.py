"""Audited continuation, answer reservation and replay invariants."""

import unittest
from unittest.mock import patch

from lost_tokens.core import RunStore
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, run_condition, validate_budget_forcing
from lost_tokens.cosine import compare_rollouts
import test_knobs as knobs


class TargetedPolicyTests(unittest.TestCase):
    setUpClass = classmethod(knobs.KnobTests.setUpClass.__func__)
    setUp = knobs.KnobTests.setUp
    eligible = staticmethod(knobs.KnobTests.eligible)
    keep = staticmethod(knobs.KnobTests.keep)
    audited = knobs.KnobTests.audited
    controlled = knobs.KnobTests.controlled

    def reserve(self):
        self.cfg["experiment"].update(
            max_output_tokens=20,
            max_branch_body_tokens=4,
            ours_budget_forcing={"force_at_body_tokens": 6, "answer_tokens": 13},
        )

    @staticmethod
    def answer_after_forcing(decoder, state, seed):
        position = len(state.generated_ids)
        answer = [ord(c) for c in r"\boxed{2}"] + [127]
        index = position - 7
        return (answer[index] if 0 <= index < len(answer) else 68), -1.0

    def run_reserved(self, store):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", self.answer_after_forcing),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            return run_condition(
                self.model, store, self.row, self.cfg, "test", "filtered_futures", lambda _: None
            )

    def test_answer_reservation_with_forks_is_audited_and_scored(self):
        self.reserve()

        class OrthogonalEncoder:
            def encode(self, texts):
                return [[float(i == j) for j in range(len(texts))] for i in range(len(texts))], sum(
                    map(len, texts)
                )

        reviewed, result = self.audited(
            "filtered_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.answer_after_forcing),
                patch(
                    "lost_tokens.recurrent_memory.compare_rollouts",
                    lambda encoder, previews, threshold: compare_rollouts(
                        OrthogonalEncoder(), previews, threshold
                    ),
                ),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertEqual([e["body_position"] for e in result["events"]], [1, 3])
        self.assertEqual(result["forced_think_end_at"], 6)
        self.assertEqual(result["prediction"], "2")
        self.assertTrue(result["correct"])
        self.assertLessEqual(len(result["body_ids"]), 20)

    def test_answer_reservation_replays_exact_body_and_context(self):
        self.reserve()
        expected = self.run_reserved(RunStore(self.root / "expected", {}))
        for stop in (4, 8, 12):
            store = PausableStore(self.root / f"resume-{stop}", {}, stop_after_calls=stop)
            with self.assertRaises(RequestedPause):
                self.run_reserved(store)
            actual = self.run_reserved(RunStore(store.path, {}, resume=True))
            self.assertEqual(actual["body_ids"], expected["body_ids"])
            self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
            self.assertEqual(actual["forced_think_end_at"], 6)
            self.assertEqual(actual["prediction"], "2")

    def test_ours_reservation_does_not_change_ar_calls_or_tokens(self):
        def run(name):
            store = RunStore(self.root / name, {})
            result = run_condition(
                self.model, store, self.row, self.cfg, "test", "plain_ar", lambda _: None
            )
            return knobs.fingerprint(result, store)

        self.cfg["experiment"]["max_output_tokens"] = 20
        before = run("ar-before")
        self.reserve()
        self.assertEqual(before, run("ar-after"))

    def test_branch_stop_and_closure_boundary_are_validated(self):
        self.reserve()
        validate_budget_forcing(self.cfg["experiment"])
        for stop in (None, True, -1, 5):
            self.cfg["experiment"]["max_branch_body_tokens"] = stop
            with self.assertRaises(ValueError):
                validate_budget_forcing(self.cfg["experiment"])

    def test_natural_thinking_end_is_not_forced_again(self):
        self.reserve()
        tokens = [126] + [ord(c) for c in r"\boxed{2}"] + [127]

        def sample(decoder, state, seed):
            return tokens[len(state.generated_ids)], -1.0

        with patch.object(StreamDecoder, "sample", sample):
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
        self.assertTrue(result["correct"])


if __name__ == "__main__":
    unittest.main()
