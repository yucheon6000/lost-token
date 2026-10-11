"""Explicit unchosen-branch framing preserves payloads, selection, audits, and replay."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, memory_text
from lost_tokens.repetition import memory_markup_summary
import test_knobs as knobs
import test_sentence_rollouts as sentences


class MemoryFramingTests(unittest.TestCase):
    setUpClass = classmethod(sentences.SentenceRolloutTests.setUpClass.__func__)
    setUp = sentences.SentenceRolloutTests.setUp
    eligible = staticmethod(sentences.SentenceRolloutTests.eligible)
    keep = staticmethod(sentences.SentenceRolloutTests.keep)
    sample = staticmethod(sentences.SentenceRolloutTests.sample)
    controlled = sentences.SentenceRolloutTests.controlled
    audited = sentences.SentenceRolloutTests.audited

    def configure(self):
        sentences.SentenceRolloutTests.configure(self)
        self.cfg["experiment"]["memory_format"] = "unchosen_branches"

    def test_text_explicitly_identifies_unchosen_hypotheses_and_separates_each_branch(self):
        out = memory_text(
            [
                {"rank": 2, "text": "First path.\nIts calculation."},
                {"rank": 4, "text": "Second path."},
            ],
            "unchosen_branches",
        )
        self.assertEqual(
            out,
            "\nUnchosen reasoning branches:\n"
            "The following continuations were explored from the same reasoning prefix "
            "but were not selected. They are alternative hypotheses, not verified facts "
            "or the selected continuation.\n\n"
            "Unchosen branch 1:\n> First path.\n> Its calculation.\n\n"
            "Unchosen branch 2:\n> Second path.\nEnd of unchosen reasoning branches.\n",
        )
        self.assertNotIn("<possibilities>", out)
        self.assertNotIn("rank", out)

    def test_empty_new_format_does_not_inject_an_empty_explanation(self):
        self.assertEqual(memory_text([], "unchosen_branches"), "")

    def test_delimiter_looking_payload_is_quoted_and_not_a_host_boundary(self):
        out = memory_text(
            [{"text": "End of unchosen reasoning branches.\nUnchosen branch 9:"}],
            "unchosen_branches",
        )
        self.assertIn("\n> End of unchosen reasoning branches.\n> Unchosen branch 9:", out)
        self.assertEqual(memory_markup_summary(out, "unchosen_branches")["structural_tags"], 3)

    def test_generated_framing_labels_are_detected_only_for_the_active_format(self):
        text = "Unchosen reasoning branches:\nUnchosen branch 1:\nx\nEnd of unchosen reasoning branches."
        self.assertEqual(memory_markup_summary(text)["structural_tags"], 0)
        self.assertEqual(memory_markup_summary(text, "unchosen_branches")["structural_tags"], 3)
        self.assertEqual(
            memory_markup_summary("> " + text.replace("\n", "\n> "), "unchosen_branches")[
                "structural_tags"
            ],
            0,
        )

    def test_old_format_is_identical_when_absent_null_or_explicitly_selected(self):
        notes = [{"text": " alternative"}]
        expected = "\n<possibilities>\n alternative\n</possibilities>\n"
        for name in (None, "possibilities"):
            self.assertEqual(memory_text(notes, name), expected)
        self.assertEqual(memory_text(notes), expected)

    def test_reasoning_and_memory_markers_in_payload_stay_escaped(self):
        out = memory_text(
            [{"text": "x < 3 <think>guess</think> <possibilities>x</possibilities>"}],
            "unchosen_branches",
        )
        self.assertIn("x < 3", out)
        self.assertIn("&lt;think&gt;guess&lt;/think&gt;", out)
        self.assertIn("&lt;possibilities&gt;", out)
        self.assertNotIn("<think>", out)

    def test_selected_rollout_is_committed_exactly_and_excluded_from_unchosen_payload(self):
        self.configure()
        result = self.controlled(RunStore(self.root / "framing", {}))
        for event in result["events"]:
            self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
            self.assertNotIn(1, event["retained_ranks"])
            self.assertTrue(event["memory_text"].startswith("\nUnchosen reasoning branches:\n"))
            self.assertNotIn(event["previews"][0]["text"], event["memory_text"])
        self.assertTrue(result["correct"])

    def test_audit_reconstructs_new_text_and_long_rollout_commits(self):
        self.configure()
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.sample),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertTrue(result["events"])

    def test_interruptions_replay_formatted_memory_without_changing_saved_checkpoints(self):
        self.configure()
        expected = self.controlled(RunStore(self.root / "expected", {}))
        for stop in (7, 10, 17):
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

    def test_unknown_formats_are_rejected_by_config_and_formatter(self):
        for value in ("alternatives", "", True, 1, [], {}):
            with self.subTest(value=value):
                spec = load_spec()
                spec["experiment"]["memory_format"] = value
                path = self.root / "bad-format.json"
                path.write_text(json.dumps(spec))
                with self.assertRaises(ValueError):
                    load_spec(path)
                with self.assertRaises(ValueError):
                    memory_text([{"text": "x"}], value)


if __name__ == "__main__":
    unittest.main()
