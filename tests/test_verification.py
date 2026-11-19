"""Single-stream verification must preserve branching, budgets, replay and audit."""

import copy
import json
import unittest
from unittest.mock import patch

from lost_tokens.audit import audit
from lost_tokens.config import validate_spec
from lost_tokens.core import RunStore, atomic_json, digest, file_digest
from lost_tokens.cosine import compare_rollouts
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, run_condition
from lost_tokens.verification import verification_plan
import test_knobs as knobs


class VerificationTests(unittest.TestCase):
    setUpClass = classmethod(knobs.KnobTests.setUpClass.__func__)
    setUp = knobs.KnobTests.setUp
    eligible = staticmethod(knobs.KnobTests.eligible)
    keep = staticmethod(knobs.KnobTests.keep)
    controlled = knobs.KnobTests.controlled
    audited = knobs.KnobTests.audited

    def enable(self):
        self.cfg["experiment"].update(
            max_output_tokens=20,
            min_branch_interval_tokens=0,
            disagreement_verification={
                "tokens": 3,
                "max_checks": 2,
                "min_body_tokens": 0,
                "min_interval_tokens": 0,
                "instruction": "Check the local constraint, then continue.",
            },
        )

    def test_enabled_checks_are_on_the_body_and_exact_selected_rollouts_survive(self):
        self.enable()
        result = self.controlled(RunStore(self.root / "enabled", {}))
        checked = [e for e in result["events"] if e.get("verification")]
        self.assertEqual(len(checked), 2)
        self.assertEqual(len(result["body_ids"]), 20)
        for event in result["events"]:
            chosen = next(p for p in event["previews"] if p["rank"] == event["selected_rank"])
            self.assertEqual(event["committed_ids"], chosen["ids"])
            position = event["body_position"]
            self.assertEqual(
                result["body_ids"][position : position + len(chosen["ids"])], chosen["ids"]
            )
        for event in checked:
            check = event["verification"]
            position = check["body_position"]
            self.assertEqual(result["body_ids"][position : position + 3], check["body_ids"])
            self.assertEqual(check["body_ids"], [68, 68, 68])

    def test_ar_and_disabled_ours_are_identical_at_every_checkpoint(self):
        for arm in ("plain_ar", "filtered_futures"):
            self.cfg["experiment"]["max_output_tokens"] = 20
            before = RunStore(self.root / (arm + "-before"), {})
            expected = knobs.fingerprint(self.controlled(before, arm), before)
            if arm == "plain_ar":
                self.enable()
            else:
                self.cfg["experiment"]["disagreement_verification"] = None
            after = RunStore(self.root / (arm + "-after"), {})
            self.assertEqual(knobs.fingerprint(self.controlled(after, arm), after), expected)
            self.cfg["experiment"].pop("disagreement_verification", None)

    def test_interrupted_checks_replay_without_rewriting_existing_checkpoints(self):
        self.enable()
        expected = self.controlled(RunStore(self.root / "expected", {}))
        for stop in (7, 8, 9, 10, 16):
            store = PausableStore(self.root / f"paused-{stop}", {}, stop_after_calls=stop)
            with self.assertRaises(RequestedPause):
                self.controlled(store)
            hashes = {p.name: file_digest(p) for p in (store.path / "checkpoints").glob("*.json")}
            actual = self.controlled(RunStore(store.path, {}, resume=True))
            self.assertEqual(actual["body_ids"], expected["body_ids"])
            self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
            self.assertEqual(
                knobs.strip_time(actual["events"]), knobs.strip_time(expected["events"])
            )
            for name, sha in hashes.items():
                self.assertEqual(file_digest(store.path / "checkpoints" / name), sha)

    def test_audit_verifies_cues_and_detects_rehashed_corrupt_check_body(self):
        self.enable()

        class Encoder:
            def encode(self, texts):
                return [[float(i == j) for j in range(len(texts))] for i in range(len(texts))], 0

        reviewed, result = self.audited(
            "filtered_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
                patch(
                    "lost_tokens.recurrent_memory.compare_rollouts",
                    lambda e, p, t: compare_rollouts(Encoder(), p, t),
                ),
            ],
        )
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertTrue(result["events"][0]["verification"])
        run = self.root / "audit-filtered_futures"
        for path in (run / "checkpoints").glob("*.json"):
            saved = json.loads(path.read_text())
            if saved["payload"]["label"].endswith("/event-0/complete"):
                saved["payload"]["result"]["verification"]["body_ids"] = [65]
                saved["sha256"] = digest(saved["payload"])
                atomic_json(path, saved)
        with self.assertRaises(AssertionError):
            audit(run, partial=True, model=self.model)

    def test_compaction_and_ttl_preserve_every_verification_body_token(self):
        self.enable()
        self.cfg["experiment"].update(
            memory_capacity_tokens=1100,
            memory_compact_to_tokens=100,
            max_event_memory_tokens=512,
            memory_ttl_tokens=4,
        )
        result = self.controlled(RunStore(self.root / "compact", {}))
        self.assertTrue(result["compactions"])
        self.assertEqual(len(result["body_ids"]), 20)
        for event in result["events"]:
            if event.get("verification"):
                check = event["verification"]
                self.assertEqual(
                    result["body_ids"][check["body_position"] : check["body_position"] + 3],
                    check["body_ids"],
                )

    def test_gate_skips_final_redundant_terminal_or_too_early_candidates(self):
        self.enable()
        exp = self.cfg["experiment"]
        event = {
            "body_position": 1,
            "retained_ranks": [2],
            "selected_rank": 1,
            "previews": [{"rank": 1, "ids": [65]}, {"rank": 2, "ids": [66]}],
        }
        self.assertIsNotNone(
            verification_plan(exp, "filtered_futures", event, [], 3, "thinking", {127}, 20)
        )
        for change, phase in [
            ({"retained_ranks": []}, "thinking"),
            ({}, "final"),
            ({"previews": [{"rank": 1, "ids": [127]}]}, "thinking"),
        ]:
            self.assertIsNone(
                verification_plan(
                    exp, "filtered_futures", {**event, **change}, [], 3, phase, {127}, 20
                )
            )
        exp["disagreement_verification"]["min_body_tokens"] = 4
        self.assertIsNone(
            verification_plan(exp, "filtered_futures", event, [], 3, "thinking", {127}, 20)
        )

    def test_forcing_boundary_limits_check_and_natural_closure_stops_checks(self):
        self.enable()
        self.cfg["experiment"].update(
            max_branch_body_tokens=4,
            ours_budget_forcing={"force_at_body_tokens": 4, "answer_tokens": 15},
        )
        self.cfg["experiment"]["max_branch_body_tokens"] = 2
        result = self.controlled(RunStore(self.root / "forcing", {}))
        self.assertEqual(result["forced_think_end_at"], 4)
        self.assertEqual(len(result["events"][0]["verification"]["body_ids"]), 1)
        self.cfg["experiment"].pop("ours_budget_forcing")
        self.cfg["experiment"].pop("max_branch_body_tokens")

        def sample(decoder, state, seed):
            return (
                126 if "[Local verification task]" in decoder.model.decode(state.ids) else 68
            ), -1.0

        with (
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", sample),
            patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
        ):
            result = run_condition(
                self.model,
                RunStore(self.root / "closure", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["verification"]["body_ids"], [126])
        self.assertTrue(result["thinking_complete"])

    def test_invalid_policy_is_rejected(self):
        self.enable()
        good = copy.deepcopy(self.cfg["experiment"]["disagreement_verification"])
        for key, bad in [
            ("tokens", 0),
            ("max_checks", True),
            ("min_body_tokens", -1),
            ("min_interval_tokens", -1),
            ("instruction", "</think>"),
        ]:
            self.cfg["experiment"]["disagreement_verification"] = {**good, key: bad}
            with self.assertRaises(ValueError):
                validate_spec(self.cfg)


if __name__ == "__main__":
    unittest.main()
