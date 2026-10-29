"""Tiny CPU models verify repeated-event semantics and interrupted recovery."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from lost_tokens.core import RunStore, file_digest, atomic_json, digest
from lost_tokens.recurrent_memory import (
    StreamDecoder,
    compact_history,
    final_response,
    run_condition,
)
from lost_tokens.protocol import PausableStore, RequestedPause, development_check
from lost_tokens.config import load_spec
from lost_tokens.cosine import compare_rollouts
import tiny_model as test_online


class ThinkingTokenizer(test_online.AsciiTokenizer):
    def encode(self, text, add_special_tokens=False):
        return super().encode(text.replace("</think>", chr(126)).replace("<think>", chr(1)))

    def decode(self, ids, skip_special_tokens=True):
        return "".join(
            ({1: "<think>", 126: "</think>", 127: "<|im_end|>"}.get(i, chr(i)))
            if not skip_special_tokens
            else (chr(i) if i not in (1, 126, 127) else "")
            for i in ids
        )


class RecurrentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_online.OnlineTests.setUpClass.__func__(cls)
        cls.model.tokenizer = ThinkingTokenizer()
        cls.model.special_ids = {1, 126, 127}
        cls.model.prompt = lambda text: cls.model.encode(text) + [1]
        cls.model.semantic_encoder = object()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = load_spec()
        self.cfg["experiment"].update(
            max_output_tokens=8,
            branch_tokens=2,
            prefill_chunk_tokens=64,
            checkpoint_body_tokens=3,
            memory_capacity_tokens=1024,
            memory_compact_to_tokens=256,
            max_event_memory_tokens=512,
            min_candidate_probability=0.05,
            min_branch_interval_tokens=0,
            selection="argmax",
            lookahead=None,
            memory_preamble=None,
        )
        self.row = {
            "id": "cpu",
            "question": "Compute 1+1.",
            "gold": "2",
            "choices": [],
            "answer_format": "math",
        }
        self.decoder = StreamDecoder(self.model, self.cfg["experiment"])

    @staticmethod
    def eligible(decoder, state):
        return {
            "eligible": True,
            "items": [
                {"rank": i + 1, "token_id": 65 + i, "text": chr(65 + i), "probability": p}
                for i, p in enumerate((0.45, 0.30, 0.20))
            ],
            "top_token_id": 65,
            "top_probability": 0.45,
            "second_probability": 0.3,
            "top_is_special": False,
            "entropy": 1.0,
        }

    @staticmethod
    def keep(*args, **kwargs):
        return {
            "retained_ranks": [2, 3],
            "cost": {},
            "embedding_cost": {"input_tokens": 0, "texts": 0, "seconds": 0.0},
        }

    def controlled(self, store, arm="filtered_futures"):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            return run_condition(self.model, store, self.row, self.cfg, "test", arm, lambda _: None)

    def test_adjacent_events_every_position_and_all_candidates(self):
        result = self.controlled(RunStore(self.root / "run", {}))
        self.assertEqual([e["body_position"] for e in result["events"]], [1, 3, 5, 7])
        self.assertEqual([c["body_position"] for c in result["checks"]], [1, 3, 5, 7])
        for event in result["events"]:
            self.assertEqual(len(event["previews"]), 3)
            self.assertEqual(event["retained_ranks"], [2, 3])
            self.assertTrue(
                all(n["origin_sha256"] == event["root_sha256"] for n in event["previews"])
            )
            self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
            self.assertNotIn("Resume", event.get("memory_text", ""))
            self.assertNotIn("Paused suffix", event.get("memory_text", ""))
        self.assertNotIn(1, result["events"][0]["retained_ranks"])
        self.assertEqual(result["body_ids"], [68, 65] * 4)

    def test_all_redundant_skips_memory_but_next_position_still_checked(self):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            patch(
                "lost_tokens.recurrent_memory.compare_rollouts",
                lambda *a, **k: {
                    "retained_ranks": [],
                    "cost": {},
                    "embedding_cost": {"input_tokens": 0, "texts": 0, "seconds": 0.0},
                },
            ),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "run", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(len(result["events"]), 4)
        self.assertTrue(all(not e["memory_ids"] for e in result["events"]))
        self.assertTrue(
            all(e["root_sha256"] == e["continuation_root_sha256"] for e in result["events"])
        )

    def test_rollouts_leave_original_cache_and_logits_unchanged(self):
        root = self.decoder.prefill([65, 66, 67])
        before = copy.deepcopy(root)
        first = self.decoder.rollout(root, 68, 12)
        self.decoder.rollout(root, 69, 13)
        self.assertEqual(first["ids"][0], 68)
        self.assertEqual(root.ids, before.ids)
        self.assertTrue(torch.equal(root.logits, before.logits))
        self.assertTrue(
            all(
                torch.equal(a.keys, b.keys) and torch.equal(a.values, b.values)
                for a, b in zip(root.cache.layers, before.cache.layers)
            )
        )

    def test_spacing_counts_body_not_memory_and_hits_exact_boundary(self):
        self.cfg["experiment"].update(max_output_tokens=20, min_branch_interval_tokens=6)
        result = self.controlled(RunStore(self.root / "spaced", {}))
        self.assertEqual([e["body_position"] for e in result["events"]], [1, 7, 13, 19])
        self.assertEqual([c["body_position"] for c in result["checks"]], [1, 7, 13, 19])
        self.assertGreater(sum(len(e["memory_ids"]) for e in result["events"]), 20)

    def test_spacing_applies_when_cosine_drops_all_alternatives(self):
        self.cfg["experiment"].update(max_output_tokens=20, min_branch_interval_tokens=5)
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            patch(
                "lost_tokens.recurrent_memory.compare_rollouts",
                lambda *a, **k: {
                    "retained_ranks": [],
                    "cost": {},
                    "embedding_cost": {"input_tokens": 0, "texts": 0, "seconds": 0.0},
                },
            ),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "spaced-empty", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual([e["body_position"] for e in result["events"]], [1, 6, 11, 16])
        self.assertTrue(all(not e["memory_ids"] for e in result["events"]))

    def test_spacing_survives_interrupted_resume_and_compaction(self):
        self.cfg["experiment"].update(
            max_output_tokens=20,
            min_branch_interval_tokens=5,
            memory_capacity_tokens=300,
            memory_compact_to_tokens=16,
            max_event_memory_tokens=256,
        )
        expected = self.controlled(RunStore(self.root / "spaced-expected", {}))
        paused = PausableStore(self.root / "spaced-resume", {}, stop_after_calls=12)
        with self.assertRaises(RequestedPause):
            self.controlled(paused)
        hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
        actual = self.controlled(RunStore(paused.path, {}, resume=True))
        self.assertEqual([e["body_position"] for e in actual["events"]], [1, 6, 11, 16])
        self.assertEqual(actual["body_ids"], expected["body_ids"])
        self.assertTrue(actual["compactions"])
        self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
        self.assertTrue(
            all(file_digest(paused.path / "checkpoints" / n) == s for n, s in hashes.items())
        )

    def test_reasoning_end_during_spacing_does_not_trigger_later_fork(self):
        self.cfg["experiment"].update(max_output_tokens=15, min_branch_interval_tokens=10)

        def sample(decoder, state, seed):
            return (126 if len(state.generated_ids) == 5 else 68), -1.0

        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", sample),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "spaced-close", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual([e["body_position"] for e in result["events"]], [1])
        self.assertTrue(result["thinking_complete"])

    def test_spacing_larger_than_budget_allows_only_first_fork(self):
        self.cfg["experiment"]["min_branch_interval_tokens"] = 256
        result = self.controlled(RunStore(self.root / "large-interval", {}))
        self.assertEqual([e["body_position"] for e in result["events"]], [1])
        self.assertEqual(len(result["body_ids"]), 8)

    def test_invalid_spacing_configuration_is_rejected(self):
        for value in (-1, 1.5, True):
            spec = load_spec()
            spec["experiment"]["min_branch_interval_tokens"] = value
            path = self.root / "invalid-spacing.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                load_spec(path)

    def test_fork_keeps_exactly_the_top_two_above_threshold(self):
        root = self.decoder.prefill([65])
        root.logits = torch.full((128,), -100.0)
        for token, p in [(65, 0.5), (66, 0.2), (43, 0.15), (67, 0.1), (68, 0.049), (69, 0.001)]:
            root.logits[token] = torch.log(torch.tensor(p))
        dist = self.decoder.candidates(root)
        self.assertEqual([i["token_id"] for i in dist["items"]], [65, 66])
        self.assertEqual([i["rank"] for i in dist["items"]], [1, 2])
        # A special second token is skipped; the next qualifying token becomes rank 2.
        root.logits[126] = torch.log(torch.tensor(0.3))
        self.assertEqual([i["token_id"] for i in self.decoder.candidates(root)["items"]], [65, 66])
        # Only one qualifying token: no fork.
        for token in (66, 43, 67, 68):
            root.logits[token] = torch.log(torch.tensor(0.01))
        self.assertFalse(self.decoder.candidates(root)["eligible"])
        root.logits[126] = 10.0
        self.assertFalse(self.decoder.candidates(root)["eligible"])

    def test_thinking_end_stops_rollout_and_scratchpad_is_not_final(self):
        root = self.decoder.prefill([65])
        out = self.decoder.rollout(root, 126, 1)
        self.assertEqual(out["ids"], [126])
        scratch = self.model.encode("answer \\boxed{2}")
        self.assertIsNone(final_response(self.model, scratch, self.row, 126)["prediction"])
        result = final_response(
            self.model, scratch + [126] + self.model.encode("Final \\boxed{2}"), self.row, 126
        )
        self.assertTrue(result["correct"])

    def test_no_interventions_after_main_thinking_end(self):
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (126, -1.0)),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "run", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(len(result["events"]), 0)
        self.assertEqual(len(result["checks"]), 0)

    def test_rollout_stops_at_multitoken_reasoning_end(self):
        self.cfg["experiment"]["branch_tokens"] = 32
        root = self.decoder.prefill([1, 65])
        closing = self.model.encode("</reasoning>")
        sequence = iter(closing[1:] + self.model.encode("MUST NOT GENERATE"))
        with patch.object(StreamDecoder, "sample", lambda *_: (next(sequence), -1.0)):
            result = self.decoder.rollout(root, closing[0], 1)
        self.assertEqual(result["ids"], closing)
        self.assertEqual(result["stop_marker"], "</reasoning>")
        self.assertEqual(result["text"], "")

    def test_selected_closing_rollout_ends_interventions(self):
        def sample(decoder, state, seed):
            return (126 if state.ids[-1] == 65 else 68), -1.0

        with (
            patch.object(StreamDecoder, "sample", sample),
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "closing", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["committed_ids"], [65, 126])

    def test_checks_only_after_literal_reasoning_start_and_before_end(self):
        stream = self.model.encode("<reasoning>abc</reasoning>tail") + [127]
        self.cfg["experiment"]["max_output_tokens"] = len(stream)
        with (
            patch.object(self.model, "prompt", lambda _: [65]),
            patch.object(
                StreamDecoder, "sample", lambda d, state, seed: (stream[len(state.ids) - 1], -1.0)
            ),
            patch.object(StreamDecoder, "candidates", lambda *_: {"eligible": False, "items": []}),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "literal", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        positions = [c["body_position"] for c in result["checks"]]
        self.assertTrue(positions)
        self.assertGreaterEqual(min(positions), len("<reasoning>") + 1)
        self.assertLess(max(positions), len("<reasoning>abc</reasoning>"))
        self.assertTrue(result["thinking_complete"])

    def test_no_reasoning_open_means_no_branches(self):
        with (
            patch.object(self.model, "prompt", lambda _: [65]),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            patch.object(StreamDecoder, "candidates", self.eligible),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "no-open", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(result["events"], [])
        self.assertEqual(result["checks"], [])

    def test_interrupted_resume_replays_without_resampling_completed_calls(self):
        expected = self.controlled(RunStore(self.root / "expected", {}))
        store = PausableStore(self.root / "resume", {}, stop_after_calls=12)
        with self.assertRaises(RequestedPause):
            self.controlled(store)
        hashes = {p.name: file_digest(p) for p in (store.path / "checkpoints").glob("*.json")}
        resumed = RunStore(store.path, {}, resume=True)
        actual = self.controlled(resumed)
        self.assertGreater(resumed.hits, 0)
        self.assertEqual(expected["body_ids"], actual["body_ids"])
        self.assertEqual(expected["final_context_sha256"], actual["final_context_sha256"])
        self.assertEqual(
            [e["root_sha256"] for e in expected["events"]],
            [e["root_sha256"] for e in actual["events"]],
        )
        self.assertTrue(
            all(file_digest(store.path / "checkpoints" / n) == s for n, s in hashes.items())
        )
        with self.assertRaises(ValueError):
            RunStore(store.path, {"changed": True}, resume=True)

    def test_compaction_only_removes_old_memory(self):
        history = [
            {"kind": "body", "ids": [1, 2]},
            {"kind": "memory", "ids": [8] * 4, "event": 0},
            {"kind": "body", "ids": [3]},
            {"kind": "memory", "ids": [9] * 2, "event": 1},
        ]
        kept, removed = compact_history(history, 3)
        self.assertEqual(removed, [0])
        self.assertEqual([i for h in kept if h["kind"] == "body" for i in h["ids"]], [1, 2, 3])

    def test_committed_blocks_survive_real_compaction(self):
        self.cfg["experiment"].update(
            memory_capacity_tokens=300, memory_compact_to_tokens=16, max_event_memory_tokens=256
        )
        store = RunStore(self.root / "compact", {})
        result = self.controlled(store)
        self.assertTrue(result["compactions"])
        self.assertEqual(result["body_ids"], [68, 65] * 4)
        for p in (store.path / "checkpoints").glob("*.json"):
            payload = json.loads(p.read_text())["payload"]
            if payload["label"].endswith("/scan"):
                request = payload["request"]
                self.assertEqual(
                    request["generated_history_sha256"],
                    digest(result["body_ids"][: request["body_position"]]),
                )

    def test_last_rollout_fits_remaining_body_budget(self):
        self.cfg["experiment"]["max_output_tokens"] = 6
        result = self.controlled(RunStore(self.root / "boundary", {}))
        self.assertEqual(len(result["body_ids"]), 6)
        self.assertEqual(result["events"][-1]["committed_ids"], [65])

    def test_configuration_rejects_single_event_restriction(self):
        spec = load_spec()
        spec["experiment"]["max_events"] = 1
        path = self.root / "invalid.json"
        path.write_text(json.dumps(spec))
        with self.assertRaises(ValueError):
            load_spec(path)

    def test_real_sampling_does_not_depend_on_checkpoint_segment_boundaries(self):
        for seed in range(10):
            uninterrupted = self.decoder.prefill([65, 66])
            full = self.decoder.segment(uninterrupted, 8, seed, 0, False)
            if len(full["ids"]) < 8:
                continue
            split = self.decoder.prefill([65, 66])
            first = self.decoder.segment(split, 2, seed, 0, False)
            second = self.decoder.segment(split, 6, seed, 2, False)
            self.assertEqual(full["ids"], first["ids"] + second["ids"])
            self.assertTrue(torch.equal(uninterrupted.logits, split.logits))
            return
        self.fail("Fixture did not produce an eight-token continuation")

    def test_encoder_receives_only_rollout_text(self):
        captured = []

        class Encoder:
            def encode(self, texts):
                captured.extend(texts)
                return [[1.0, 0.0], [0.0, 1.0]], 4

        notes = [
            {"rank": 1, "text": "reference fragment"},
            {"rank": 2, "text": "alternative fragment"},
        ]
        result = compare_rollouts(Encoder(), notes, 0.9)
        self.assertEqual(captured, ["reference fragment", "alternative fragment"])
        self.assertEqual(result["retained_ranks"], [2])
        self.assertEqual(result["similarity_matrix"][0][1], 0.0)

    def test_eos_without_think_is_scored_separately_from_format(self):
        body = self.model.encode("Final answer: \\boxed{2}") + [127]
        result = final_response(self.model, body, self.row, 126)
        self.assertTrue(result["correct"])
        self.assertFalse(result["thinking_complete"])
        self.assertEqual(result["answer_source"], "eos_without_thinking_end")
        self.assertIsNone(result["thinking_tokens"])

    def test_development_check_blocks_missing_answers_without_using_gold(self):
        cases = [
            {
                "conditions": {
                    a: {
                        "prediction": None,
                        "body_text": "unfinished",
                        "body_ids": [65],
                        "correct": True,
                    }
                    for a in self.cfg["experiment"]["arms"]
                }
            }
        ]
        self.assertFalse(development_check(cases, self.cfg)["passed"])
        for r in cases[0]["conditions"].values():
            r.update(prediction="wrong answer", correct=False)
        self.assertTrue(development_check(cases, self.cfg)["passed"])
        cases[0]["conditions"]["plain_ar"]["body_text"] = "<possibilities>"
        self.assertFalse(development_check(cases, self.cfg)["passed"])

    def test_inline_tag_mention_is_not_a_structural_memory_block(self):
        cases = [
            {
                "conditions": {
                    a: {
                        "prediction": "A",
                        "body_text": "The instruction mentions `<possibilities>`, which is irrelevant here.",
                        "body_ids": [65, 66, 67],
                    }
                    for a in self.cfg["experiment"]["arms"]
                }
            }
        ]
        result = development_check(cases, self.cfg)
        self.assertTrue(result["passed"])
        self.assertEqual(result["arms"]["plain_ar"]["inline_memory_mentions"], 1)

    def test_injected_tokens_do_not_enter_repetition_history(self):
        state = self.decoder.prefill([65] * 80)
        self.assertEqual(state.generated_ids, [])
        self.decoder.advance(state, [66] * 4, generated=True)
        self.decoder.advance(state, [67] * 80, block_size=64)
        self.assertEqual(state.generated_ids, [66] * 4)

    def test_guard_breaks_exact_loop_and_resume_restores_its_history(self):
        self.cfg["experiment"].update(
            max_output_tokens=12,
            repetition_guard={
                "enabled": True,
                "min_span_tokens": 4,
                "min_cycles": 4,
                "max_period_tokens": 1,
            },
        )
        original = StreamDecoder.sample

        def sampling(decoder, state, seed):
            state.logits = torch.full((128,), -100.0)
            state.logits[68] = 10.0
            state.logits[69] = 9.0
            return original(decoder, state, seed)

        def execute(store):
            with patch.object(StreamDecoder, "sample", sampling):
                return run_condition(
                    self.model, store, self.row, self.cfg, "test", "plain_ar", lambda _: None
                )

        expected = execute(RunStore(self.root / "guard-expected", {}))
        self.assertTrue(expected["body_guard_events"])
        self.assertTrue(
            all(g["sampled_token"] != g["blocked_token"] for g in expected["body_guard_events"])
        )
        paused = PausableStore(self.root / "guard-resume", {}, stop_after_calls=3)
        with self.assertRaises(RequestedPause):
            execute(paused)
        actual = execute(RunStore(paused.path, {}, resume=True))
        self.assertEqual(actual["body_ids"], expected["body_ids"])
        self.assertEqual(actual["body_guard_events"], expected["body_guard_events"])

    def test_no_fork_conditions_identical_without_batch_shape_changes(self):
        outputs = []
        with patch.object(StreamDecoder, "candidates", lambda *_: {"eligible": False, "items": []}):
            for arm in ("plain_ar", "reference_only", "all_futures", "filtered_futures"):
                outputs.append(
                    run_condition(
                        self.model,
                        RunStore(self.root / arm, {}),
                        self.row,
                        self.cfg,
                        "test",
                        arm,
                        lambda _: None,
                    )
                )
        self.assertTrue(all(r["body_ids"] == outputs[0]["body_ids"] for r in outputs))

    def test_audit_detects_changed_event_in_a_completed_condition(self):
        from lost_tokens.audit import audit

        self.row["task"] = "fixture"
        cfg = copy.deepcopy(self.cfg)
        cfg["experiment"]["arms"] = ["reference_only"]
        cfg["datasets"] = [{"name": "fixture"}]
        cfg["smoke"] = {"tasks": ["fixture"], "cases_per_task": 1}
        split = {"tasks": {"fixture": {"development": [self.row]}}}
        identity = {"spec": cfg, "source": {}, "split_sha256": digest(split), "mode": "smoke"}
        store = RunStore(self.root / "audit", identity)
        atomic_json(store.path / "split.json", split)
        atomic_json(store.path / "resolved-config.json", cfg)
        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
        ):
            result = run_condition(
                self.model, store, self.row, cfg, "smoke/fixture", "reference_only", lambda _: None
            )
        store.call("smoke/fixture/cpu/reference_only/complete", {}, lambda: result)
        reviewed = audit(store.path, partial=True, model=self.model)
        self.assertEqual(reviewed["events"], 4)
        self.assertEqual(reviewed["completed_conditions"], 1)
        path = next(
            p
            for p in (store.path / "checkpoints").glob("*.json")
            if json.loads(p.read_text())["payload"]["label"]
            == "smoke/fixture/cpu/reference_only/complete"
        )
        item = json.loads(path.read_text())
        item["payload"]["result"]["events"][1]["root_sha256"] = "bad"
        item["sha256"] = digest(item["payload"])
        atomic_json(path, item)
        with self.assertRaises(AssertionError):
            audit(store.path, partial=True, model=self.model)


if __name__ == "__main__":
    unittest.main()
