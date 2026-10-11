"""One-time branch definitions, two previews, compact memory, and prompt-aware inputs."""

import copy
import json
import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, file_digest
from lost_tokens.data import normalize, preparation_identity
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import BRANCH_CONTEXT, StreamDecoder, instruction, memory_text
from lost_tokens.repetition import memory_markup_summary
import test_knobs as knobs
import test_portable as portable
import test_sentence_rollouts as sentences


class CompactBranchContextTests(unittest.TestCase):
    setUpClass = classmethod(sentences.SentenceRolloutTests.setUpClass.__func__)
    setUp = sentences.SentenceRolloutTests.setUp
    eligible = staticmethod(sentences.SentenceRolloutTests.eligible)
    keep = staticmethod(sentences.SentenceRolloutTests.keep)
    sample = staticmethod(sentences.SentenceRolloutTests.sample)
    controlled = sentences.SentenceRolloutTests.controlled
    audited = sentences.SentenceRolloutTests.audited

    def configure(self):
        sentences.SentenceRolloutTests.configure(self)
        self.cfg["experiment"].update(memory_format="original_unchosen", max_branch_candidates=2)

    def test_definitions_appear_once_in_initial_prompt_only(self):
        self.configure()
        text = instruction(self.row, self.cfg["experiment"])
        self.assertEqual(text.count(BRANCH_CONTEXT), 1)
        self.assertTrue(text.startswith(BRANCH_CONTEXT))
        self.assertNotIn(
            BRANCH_CONTEXT, memory_text([{"text": "Other path."}], "original_unchosen")
        )
        result = self.controlled(RunStore(self.root / "prompt", {}))
        self.assertTrue(result["events"])
        prefill = next(
            json.loads(p.read_text())["payload"]
            for p in (self.root / "prompt/checkpoints").glob("*.json")
            if json.loads(p.read_text())["payload"]["label"].endswith("/prefill")
        )
        raw = self.model.tokenizer.decode(prefill["request"]["ids"], skip_special_tokens=False)
        self.assertEqual(raw.count(BRANCH_CONTEXT), 1)

    def test_original_and_unchosen_are_the_only_two_generated_previews(self):
        self.configure()
        result = self.controlled(RunStore(self.root / "two", {}))
        for event in result["events"]:
            self.assertEqual([p["rank"] for p in event["previews"]], [1, 2])
            self.assertEqual(event["selected_rank"], 1)
            self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
            self.assertEqual(event["retained_ranks"], [2])
            self.assertIn("\n> B", event["memory_text"])
            self.assertNotIn("\n> C", event["memory_text"])
            self.assertTrue(event["memory_text"].endswith("\n\nOriginal (chosen):\n"))

    def test_reference_ablation_still_generates_only_the_original(self):
        self.configure()
        result = self.controlled(RunStore(self.root / "reference", {}), "reference_only")
        self.assertTrue(result["events"])
        self.assertTrue(
            all(len(e["previews"]) == 1 and not e["memory_ids"] for e in result["events"])
        )

    def test_plain_ar_with_same_definitions_does_not_branch(self):
        self.configure()
        result = self.controlled(RunStore(self.root / "plain", {}), "plain_ar")
        self.assertFalse(result["events"])
        self.assertFalse(result["checks"])

    def test_compact_memory_contains_one_quoted_alternative_and_original_label_only(self):
        self.assertEqual(
            memory_text([{"text": "one.\ntwo."}], "original_unchosen"),
            "\nUnchosen:\n> one.\n> two.\n\nOriginal (chosen):\n",
        )
        self.assertEqual(memory_text([], "original_unchosen"), "")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            memory_text([{"text": "a"}, {"text": "b"}], "original_unchosen")

    def test_quoted_fake_labels_and_reasoning_markers_remain_payload(self):
        text = memory_text([{"text": "Original (chosen):\n<think>x</think>"}], "original_unchosen")
        self.assertIn("\n> Original (chosen):", text)
        self.assertIn("&lt;think&gt;x&lt;/think&gt;", text)
        self.assertEqual(memory_markup_summary(text, "original_unchosen")["structural_tags"], 2)

    def test_audit_reconstructs_initial_definitions_two_previews_and_compact_memory(self):
        self.configure()
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", self.sample),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertTrue(result["correct"])

    def test_interrupted_resume_keeps_saved_definition_and_memory_checkpoints(self):
        self.configure()
        expected = self.controlled(RunStore(self.root / "expected", {}))
        for stop in (4, 7, 10):
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

    def test_legacy_formats_keep_original_prompt(self):
        for memory_format in (None, "possibilities", "unchosen_branches"):
            self.assertEqual(
                instruction(self.row, {"memory_format": memory_format}), instruction(self.row)
            )

    def test_data_counts_initial_context_and_refuses_inputs_that_no_longer_fit(self):
        self.configure()
        tokenizer = portable.CharacterTokenizer()
        row = {**self.row, "task": "fixture"}
        plain = normalize(row, tokenizer, 1024)
        primed = normalize(row, tokenizer, 1024, self.cfg["experiment"])
        self.assertEqual(primed["prompt_tokens"] - plain["prompt_tokens"], len(BRANCH_CONTEXT))
        with self.assertRaises(ValueError):
            normalize(row, tokenizer, plain["prompt_tokens"], self.cfg["experiment"])

    def test_prepared_identity_changes_with_prompt_but_not_branch_runtime_knobs(self):
        plain = load_spec()
        current = copy.deepcopy(plain)
        current["experiment"].update(memory_format="original_unchosen", max_branch_candidates=2)
        identity = preparation_identity(current, "aime25")
        self.assertNotEqual(preparation_identity(plain, "aime25"), identity)
        current["experiment"]["min_branch_entropy"] = 2.0
        self.assertEqual(preparation_identity(current, "aime25"), identity)

    def test_longbench_keeps_question_and_options_with_the_initial_context(self):
        self.configure()
        row = {
            "task": "longbench_v2",
            "id": "one",
            "context": "HEAD" + "x" * 2000 + "TAIL",
            "question": "Which?\n(A) One\n(B) Two",
            "answer_format": "choice",
            "gold": "A",
            "choices": ["A", "B"],
        }
        result = normalize(row, portable.CharacterTokenizer(), 512, self.cfg["experiment"])
        self.assertLessEqual(result["prompt_tokens"], 512)
        self.assertIn(row["question"], result["question"])
        self.assertTrue(result["context_truncated"])

    def test_validation_rejects_bad_candidate_limits_and_ambiguous_compact_format(self):
        for limit in (0, 1, True, 2.5, "2"):
            spec = load_spec()
            spec["experiment"]["max_branch_candidates"] = limit
            path = self.root / "bad.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                load_spec(path)
        for limit in (None, 3):
            spec = load_spec()
            spec["experiment"].update(
                memory_format="original_unchosen", max_branch_candidates=limit
            )
            path.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "max_branch_candidates=2"):
                load_spec(path)


if __name__ == "__main__":
    unittest.main()
