"""Sentence-count rollouts preserve caches, body budgets, audits, and recovery."""

import copy
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, new_sentence_ends, run_condition
from lost_tokens.runner import CheckpointStore, DeadlineReached
import test_knobs as knobs
import test_recurrent_memory as base


class SentenceRolloutTests(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    setUp = base.RecurrentTests.setUp
    eligible = staticmethod(base.RecurrentTests.eligible)
    keep = staticmethod(base.RecurrentTests.keep)
    audited = knobs.KnobTests.audited

    def configure(self):
        self.cfg["experiment"].update(
            branch_tokens=2,
            max_output_tokens=80,
            rollout_sentence_ends=2,
            min_branch_entropy=1.0,
            budget_forcing={"force_at_body_tokens": 39, "answer_tokens": 40},
        )

    @staticmethod
    def sample(decoder, state, seed):
        history = state.generated_ids
        if 126 in history:
            answer = list(map(ord, "\\boxed{2}")) + [127]
            offset = len(history) - history.index(126) - 1
            return answer[min(offset, len(answer) - 1)], -1.0
        starts = [i for i, token in enumerate(history) if token in (65, 66, 67)]
        if starts:
            text = " one. two. "
            offset = len(history) - starts[-1] - 1
            if offset < len(text):
                return ord(text[offset]), -1.0
        return 120, -1.0

    def controlled(self, store, arm="filtered_futures"):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", self.sample),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            return run_condition(self.model, store, self.row, self.cfg, "test", arm, lambda _: None)

    def rollout(self, text, count=200):
        self.cfg["experiment"].update(branch_tokens=2, rollout_sentence_ends=2)
        ids = self.model.encode(text)
        remaining = iter(ids[1:] + [120] * count)
        root = self.decoder.prefill([1, 65])
        original = copy.deepcopy(root)
        with patch.object(StreamDecoder, "sample", lambda *_: (next(remaining), -1.0)):
            result = self.decoder.rollout(root, ids[0], 11, count)
        self.assertEqual(root.ids, original.ids)
        return result

    def test_short_sentences_stop_without_minimum_token_length(self):
        result = self.rollout("A. B. NEVER_GENERATE")
        self.assertEqual(self.model.decode(result["ids"]), "A. B. ")
        self.assertEqual(result["sentence_ends"], 2)
        self.assertLess(len(result["ids"]), 13)

    def test_long_sentences_are_not_cut_at_old_32_or_proposed_64_token_caps(self):
        text = "a" * 90 + ". " + "b" * 20 + ". "
        result = self.rollout(text + "NEVER_GENERATE")
        self.assertEqual(self.model.decode(result["ids"]), text)
        self.assertGreater(len(result["ids"]), 64)
        self.assertEqual(result["sentence_ends"], 2)

    def test_decimals_and_abbreviations_do_not_finish_sentences(self):
        text = "Dr. X sees 3.14, e.g. a value. It equals 3.14. "
        result = self.rollout(text + "NEVER_GENERATE")
        self.assertEqual(self.model.decode(result["ids"]), text)
        self.assertEqual(result["sentence_ends"], 2)

    def test_numbered_list_prefixes_are_not_sentence_endings(self):
        text = "1. First option.\n2. Second option. "
        result = self.rollout(text + "NEVER_GENERATE")
        self.assertEqual(self.model.decode(result["ids"]), text)

    def test_numerical_sentence_can_end_with_a_newline(self):
        text = "42.\nNext sentence. "
        self.assertEqual(self.model.decode(self.rollout(text + "TAIL")["ids"]), text)

    def test_punctuation_groups_and_closing_quotes_count_once(self):
        for text in ("Really?! Yes! ", 'He said "yes." Then left. ', "Maybe... Next. "):
            with self.subTest(text=text):
                self.assertEqual(self.model.decode(self.rollout(text + "TAIL")["ids"]), text)

    def test_whitespace_newlines_and_backslashes_alone_do_not_finish_sentences(self):
        result = self.rollout("abc\n\n\\\\ xyz " * 3, count=45)
        self.assertEqual(len(result["ids"]), 45)
        self.assertEqual(result["sentence_ends"], 0)

    def test_eos_and_reasoning_end_stop_before_two_sentences(self):
        for token in (126, 127):
            with self.subTest(token=token):
                result = self.rollout("abc" + chr(token) + "TAIL")
                self.assertEqual(result["ids"], [97, 98, 99, token])
                self.assertEqual(result["sentence_ends"], 0)

    def test_remaining_budget_is_a_hard_limit_when_no_sentence_ends_exist(self):
        result = self.rollout("a" * 90, count=75)
        self.assertEqual(len(result["ids"]), 75)
        self.assertEqual(result["sentence_ends"], 0)

    def test_counted_boundaries_are_not_recounted_on_more_whitespace(self):
        ids = self.model.encode("One. \n\n Two. \n")
        self.assertEqual(
            sum(new_sentence_ends(self.model, ids[: i + 1]) for i in range(len(ids))), 2
        )
        self.assertEqual(new_sentence_ends(self.model, []), 0)

    def test_full_width_punctuation_works_without_spaces(self):
        decode = self.model.decode
        with patch.object(self.model, "decode", lambda ids: decode(ids).replace("Z", "。")):
            result = self.rollout("abcZdefZTAIL")
        self.assertEqual(len(result["ids"]), 8)
        self.assertEqual(result["sentence_ends"], 2)

    def test_sentence_rollout_requires_explicit_body_budget(self):
        self.cfg["experiment"]["rollout_sentence_ends"] = 2
        with self.assertRaisesRegex(ValueError, "remaining body budget"):
            self.decoder.rollout(self.decoder.prefill([1, 65]), 66, 1)

    def test_all_arms_fit_thinking_budget_and_commit_selected_rollout_exactly(self):
        self.configure()
        for arm in ("reference_only", "all_futures", "filtered_futures"):
            result = self.controlled(RunStore(self.root / arm, {}), arm)
            self.assertEqual(result["forced_think_end_at"], 39)
            self.assertTrue(result["correct"])
            for event in result["events"]:
                self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
                self.assertLessEqual(event["body_position"] + len(event["committed_ids"]), 39)
            self.assertEqual(result["events"][0]["previews"][0]["sentence_ends"], 2)
            self.assertGreater(len(result["events"][0]["committed_ids"]), 2)

    def test_sentence_rollout_audit_and_interrupted_resume(self):
        self.configure()
        reviewed, _ = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.sample),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        expected = self.controlled(RunStore(self.root / "expected", {}))
        for stop in (3, 7, 10, 17):
            paused = PausableStore(self.root / f"resume-{stop}", {}, stop_after_calls=stop)
            with self.assertRaises(RequestedPause):
                self.controlled(paused)
            hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
            actual = self.controlled(RunStore(paused.path, {}, resume=True))
            self.assertEqual(knobs.strip_time(actual), knobs.strip_time(expected))
            self.assertTrue(
                all(
                    file_digest(paused.path / "checkpoints" / name) == sha
                    for name, sha in hashes.items()
                )
            )

    def test_long_rollout_observes_worker_deadline_between_tokens(self):
        self.cfg["experiment"]["rollout_sentence_ends"] = 2
        store = CheckpointStore(self.root / "deadline", {}, deadline=time.time() + 60)
        root = self.decoder.prefill([1, 65])
        self.decoder.check_deadline = store.check_deadline

        def expire(*args):
            store.deadline = time.monotonic() - 1
            return 120, -1.0

        with patch.object(StreamDecoder, "sample", expire):
            with self.assertRaises(DeadlineReached):
                self.decoder.rollout(root, 66, 1, 500)
        self.assertEqual(root.ids, [1, 65])

    def test_config_rejects_bad_counts_and_conflicting_stopping_rules(self):
        for value in (0, -1, True, 1.5, "2"):
            spec = load_spec()
            spec["experiment"]["rollout_sentence_ends"] = value
            path = self.root / "bad.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                load_spec(path)
        spec = load_spec()
        spec["experiment"].update(
            rollout_sentence_ends=2, rollout_early_stop={"min_tokens": 13, "patterns": [". "]}
        )
        path.write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, "not both"):
            load_spec(path)

    def test_new_profile_preserves_previous_configuration_except_selected_controls(self):
        root = Path(__file__).resolve().parents[1]
        previous = load_spec(root / "configs/bounded-entropy-sentence.json")
        current = load_spec(root / "configs/sparse-sentence-rollouts.json")
        self.assertEqual(current["experiment"]["min_branch_entropy"], 1.0)
        self.assertEqual(current["experiment"].pop("rollout_sentence_ends"), 2)
        previous["experiment"].pop("rollout_early_stop")
        previous["experiment"]["min_branch_entropy"] = 1.0
        self.assertEqual(current, previous)


if __name__ == "__main__":
    unittest.main()
