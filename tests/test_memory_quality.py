"""Quality-filtered unchosen memory: decisions, exact commits, audit and replay."""

import copy
import json
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, atomic_json, digest, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import (
    StreamDecoder,
    memory_quality_gate,
    run_condition,
    select_rollout,
    validate_memory_quality_gate,
)
import test_knobs as knobs
import test_recurrent_memory as base
from test_lookahead import preview


class MemoryQualityDecisions(unittest.TestCase):
    def exp(self):
        return {
            "selection": "lookahead",
            "lookahead": {
                "statistic": "mean_logprob",
                "margin": 0.1,
                "min_tokens": 1,
            },
            "memory_quality_gate": {"max_score_gap": 0.1},
        }

    def gate(self, previews, exp=None):
        exp = exp or self.exp()
        selection = select_rollout(previews, exp, {127})
        return selection, memory_quality_gate(previews, selection, exp)

    def test_only_close_eligible_alternatives_are_memory(self):
        _, gate = self.gate(
            [preview(1, [-0.1, -0.2]), preview(2, [-0.1, -0.25]), preview(3, [-0.1, -2.0])]
        )
        self.assertEqual(gate["retained_ranks"], [2])
        self.assertIn("score_gap", gate["scores"][2]["reasons"])
        self.assertFalse(gate["scores"][0]["accepted"])

    def test_selected_reference_can_be_non_rank_one(self):
        selection, gate = self.gate(
            [preview(1, [-0.1, -2.0]), preview(2, [-0.1, -0.2]), preview(3, [-0.1, -0.25])]
        )
        self.assertEqual(selection["selected_rank"], 2)
        self.assertEqual(gate["reference_rank"], 2)
        self.assertEqual(gate["retained_ranks"], [3])

    def test_forced_first_token_and_doubt_penalty_do_not_rank_memory(self):
        exp = self.exp()
        exp["lookahead"]["contradiction_penalty"] = 0.25
        selection, gate = self.gate(
            [
                preview(1, [-100.0, -0.25], text="Wait, correct the algebra"),
                preview(2, [-0.1, -0.35], text="Proceed"),
            ],
            exp,
        )
        self.assertEqual(selection["selected_rank"], 2)
        self.assertEqual(gate["retained_ranks"], [1])
        self.assertEqual(gate["scores"][0]["value"], -0.25)

    def test_short_terminal_blank_and_ineligible_reference_supply_no_memory(self):
        _, gate = self.gate(
            [
                preview(1, [-0.1, -0.2]),
                preview(2, [-0.1]),
                preview(3, [-0.1, -0.2], stop_marker="</think>"),
                preview(4, [-0.1, -0.2], text=" "),
            ]
        )
        self.assertEqual(gate["retained_ranks"], [])
        _, gate = self.gate([preview(1, [-0.1], stop_marker="</think>"), preview(2, [-0.1, -0.1])])
        self.assertFalse(gate["reference_eligible"])
        self.assertEqual(gate["retained_ranks"], [])

    def test_invalid_gate_settings_rejected(self):
        for value in (True, -0.1, float("nan"), float("inf"), "0.1"):
            with self.subTest(value=value):
                exp = self.exp()
                exp["memory_quality_gate"]["max_score_gap"] = value
                with self.assertRaises(ValueError):
                    validate_memory_quality_gate(exp)
        exp = self.exp()
        exp["selection"] = "argmax"
        with self.assertRaises(ValueError):
            validate_memory_quality_gate(exp)

    def test_new_config_changes_only_memory_gate(self):
        current = load_spec("configs/vllm-ours-quality-memory.json")
        self.assertEqual(current["experiment"].pop("memory_quality_gate"), {"max_score_gap": 0.1})
        self.assertEqual(current, load_spec("configs/vllm-ours-answer-reserve.json"))


class MemoryQualityProtocol(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    eligible = staticmethod(base.RecurrentTests.eligible)
    audited = knobs.KnobTests.audited

    def setUp(self):
        base.RecurrentTests.setUp(self)
        self.cfg["experiment"].update(
            selection="lookahead",
            lookahead={
                "statistic": "mean_logprob",
                "margin": 0.1,
                "min_tokens": 1,
            },
            memory_quality_gate={"max_score_gap": 0.1},
        )
        self.cfg["similarity"]["min_threshold"] = None

    def patches(self):
        class Encoder:
            def encode(self, texts):
                # B and C are duplicates; B must be removed before it can suppress C.
                return [[1.0, 0.0] if t.startswith("A") else [0.0, 1.0] for t in texts], sum(
                    map(len, texts)
                )

        def sample(decoder, state, seed):
            return 68, (
                -2.0 if 66 in state.generated_ids else -0.25 if 67 in state.generated_ids else -0.2
            )

        return [
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", sample),
            patch.object(self.model, "semantic_encoder", Encoder()),
        ]

    def run_with(self, store, arm="filtered_futures"):
        with ExitStack() as stack:
            for patcher in self.patches():
                stack.enter_context(patcher)
            return run_condition(self.model, store, self.row, self.cfg, "test", arm, lambda _: None)

    def test_quality_precedes_cosine_and_full_selected_rollout_is_committed(self):
        reviewed, result = self.audited("filtered_futures", self.patches())
        self.assertEqual(reviewed["completed_conditions"], 1)
        for event in result["events"][:-1]:
            self.assertEqual(event["memory_quality"]["retained_ranks"], [3])
            self.assertEqual(event["similarity"]["ranks"], [1, 3])
            self.assertEqual(event["retained_ranks"], [3])
            selected = event["previews"][0]
            self.assertEqual(event["selected_rank"], 1)
            self.assertEqual(event["committed_ids"], selected["ids"])
            self.assertEqual(len(event["committed_ids"]), 2)

    def test_explicit_off_is_identical_and_non_ours_arms_are_unchanged(self):
        self.cfg["experiment"].pop("memory_quality_gate")
        absent = knobs.fingerprint(self.run_with(s := RunStore(self.root / "off-absent", {})), s)
        self.cfg["experiment"]["memory_quality_gate"] = None
        explicit = knobs.fingerprint(self.run_with(s := RunStore(self.root / "off-null", {})), s)
        self.assertEqual(absent, explicit)
        for arm in ("plain_ar", "reference_only", "selected_only", "all_futures"):
            original = knobs.fingerprint(
                self.run_with(s := RunStore(self.root / (arm + "-off"), {}), arm), s
            )
            self.cfg["experiment"]["memory_quality_gate"] = {"max_score_gap": 0.1}
            current = knobs.fingerprint(
                self.run_with(s := RunStore(self.root / (arm + "-on"), {}), arm), s
            )
            self.assertEqual(original, current)
            self.cfg["experiment"]["memory_quality_gate"] = None

    def test_resume_preserves_quality_decisions_memory_and_saved_calls(self):
        expected = self.run_with(RunStore(self.root / "expected", {}))
        for stop in (1, 5, 12, 20, 30):
            paused = PausableStore(self.root / f"resume-{stop}", {}, stop_after_calls=stop)
            try:
                self.run_with(paused)
            except RequestedPause:
                pass
            hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
            actual = self.run_with(RunStore(paused.path, {}, resume=True))
            self.assertEqual(knobs.strip_time(actual), knobs.strip_time(expected))
            self.assertTrue(
                all(
                    file_digest(paused.path / "checkpoints" / n) == sha for n, sha in hashes.items()
                )
            )

    def test_quality_gate_and_answer_reservation_audit_together(self):
        self.cfg["experiment"].update(
            max_output_tokens=16,
            max_branch_body_tokens=4,
            ours_budget_forcing={"force_at_body_tokens": 5, "answer_tokens": 9},
        )
        scripted = knobs.KnobTests.scripted(self, "DDDDD" + chr(126) + "\\boxed{2}")
        reviewed, result = self.audited(
            "filtered_futures", self.patches() + [patch.object(StreamDecoder, "sample", scripted)]
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertEqual(result["forced_think_end_at"], 5)
        self.assertEqual(result["prediction"], "2")
        self.assertTrue(result["correct"])
        self.assertTrue(all("memory_quality" in event for event in result["events"]))
        self.assertLessEqual(len(result["body_ids"]), 16)

    def test_audit_rejects_consistently_tampered_quality_metadata(self):
        from lost_tokens.audit import audit

        self.audited("filtered_futures", self.patches())
        run = self.root / "audit-filtered_futures"
        for path in (run / "checkpoints").glob("*.json"):
            saved = json.loads(path.read_text())
            result = saved["payload"]["result"]
            if not isinstance(result, dict):
                continue
            events = result.get("events", [])
            if "memory_quality" in result:
                events = [result]
            changed = False
            for event in events:
                if "memory_quality" in event:
                    event["memory_quality"]["max_score_gap"] = 100.0
                    changed = True
            if changed:
                saved["sha256"] = digest(saved["payload"])
                atomic_json(path, saved)
        with self.assertRaises(AssertionError):
            audit(run, partial=True, model=self.model)
