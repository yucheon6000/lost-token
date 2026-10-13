"""Experiment knobs A (max_memory_events), B, D (memory TTL) and F (budget forcing).

The defaults-unchanged invariant is pinned by knob_defaults_golden.json, which was
generated with the code from before the knobs existed.
"""

import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lost_tokens.core import RunStore, file_digest, atomic_json, digest, derived_seed
from lost_tokens.recurrent_memory import StreamDecoder, instruction, run_condition
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.config import load_spec
import test_recurrent_memory as base


def strip_time(value):
    if isinstance(value, dict):
        return {
            k: strip_time(v) for k, v in value.items() if k not in ("seconds", "recovery_seconds")
        }
    if isinstance(value, list):
        return [strip_time(v) for v in value]
    return value


def fingerprint(result, store):
    """Identity of a finished condition: every checkpoint label/request plus timing-free result."""
    saved = [
        json.loads(p.read_text())["payload"] for p in (store.path / "checkpoints").glob("*.json")
    ]
    return {
        "labels_requests": digest(sorted((p["label"], p["request"]) for p in saved)),
        "results": digest(sorted((p["label"], strip_time(p["result"])) for p in saved)),
        "condition": digest(strip_time(result)),
        "body_ids": result["body_ids"],
    }


class KnobTests(unittest.TestCase):
    """Reuses the tiny-model fixture of RecurrentTests without re-running its tests."""

    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    setUp = base.RecurrentTests.setUp
    eligible = staticmethod(base.RecurrentTests.eligible)
    keep = staticmethod(base.RecurrentTests.keep)
    controlled = base.RecurrentTests.controlled

    ANSWER = "\\boxed{2}"

    def scripted(self, text):
        ids = [ord(c) for c in text]
        return lambda decoder, state, seed: (
            (ids[len(state.generated_ids)] if len(state.generated_ids) < len(ids) else 68),
            -1.0,
        )

    def plain(self, store, sample=None, arm="plain_ar"):
        with patch.object(StreamDecoder, "sample", sample or (lambda *_: (68, -1.0))):
            return run_condition(self.model, store, self.row, self.cfg, "test", arm, lambda _: None)

    def memory_run(self, name, **knobs):
        self.cfg["experiment"].update(knobs)
        return self.controlled(RunStore(self.root / name, {}), arm="all_futures")

    # ---- defaults unchanged -------------------------------------------------
    def default_runs(self):
        out = {}
        out["controlled"] = self.run_fp("d1", lambda s: self.controlled(s))
        self.cfg["experiment"].update(
            max_output_tokens=20,
            min_branch_interval_tokens=5,
            memory_capacity_tokens=300,
            memory_compact_to_tokens=16,
            max_event_memory_tokens=256,
        )
        out["compaction"] = self.run_fp("d2", lambda s: self.controlled(s))
        out["plain_real"] = self.run_fp(
            "d3",
            lambda s: run_condition(
                self.model, s, self.row, self.cfg, "test", "plain_ar", lambda _: None
            ),
        )
        return out

    def run_fp(self, name, call):
        store = RunStore(self.root / name, {})
        return fingerprint(call(store), store)

    def test_defaults_match_pre_change_golden(self):
        golden = json.loads((Path(__file__).parent / "knob_defaults_golden.json").read_text())
        self.assertEqual(self.default_runs(), golden)

    def test_explicit_off_knobs_equal_absent_knobs(self):
        absent = self.default_runs()
        base.RecurrentTests.setUp(self)
        self.cfg["experiment"].update(
            max_memory_events=None,
            min_branch_body_tokens=0,
            memory_ttl_tokens=None,
            budget_forcing=None,
            min_branch_entropy=None,
            rollout_early_stop=None,
        )
        self.assertEqual(self.default_runs(), absent)

    # ---- A ------------------------------------------------------------------
    def test_max_memory_events_stops_forks_after_n_injections(self):
        base = self.memory_run("a0", max_memory_events=None)
        self.assertEqual(len(base["events"]), 4)
        result = self.memory_run("a2", max_memory_events=2)
        self.assertEqual([e["body_position"] for e in result["events"]], [1, 3])
        self.assertEqual(sum(bool(e["memory_ids"]) for e in result["events"]), 2)
        self.assertEqual(len(result["body_ids"]), 8)
        self.assertEqual([c["body_position"] for c in result["checks"]], [1, 3])

    def test_max_memory_events_counts_only_injecting_events(self):
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
            self.cfg["experiment"]["max_memory_events"] = 1
            result = run_condition(
                self.model,
                RunStore(self.root / "a-empty", {}),
                self.row,
                self.cfg,
                "test",
                "filtered_futures",
                lambda _: None,
            )
        self.assertEqual(len(result["events"]), 4)

    # ---- B ------------------------------------------------------------------
    def test_min_branch_body_tokens_delays_first_fork(self):
        result = self.memory_run("b4", min_branch_body_tokens=4)
        self.assertEqual([e["body_position"] for e in result["events"]], [4, 6])
        self.assertEqual([c["body_position"] for c in result["checks"]], [4, 6])
        self.assertEqual(len(result["body_ids"]), 8)

    def test_min_branch_body_tokens_applies_to_every_scanning_arm(self):
        self.cfg["experiment"]["min_branch_body_tokens"] = 5
        for arm in ("reference_only", "all_futures", "filtered_futures"):
            result = self.controlled(RunStore(self.root / arm, {}), arm=arm)
            self.assertTrue(result["events"])
            self.assertTrue(all(e["body_position"] >= 5 for e in result["events"]))

    # ---- D ------------------------------------------------------------------
    def test_memory_ttl_drops_old_blocks_and_preserves_body(self):
        base = self.memory_run("d-base", memory_ttl_tokens=None)
        self.assertEqual(base["retained_memory_events"], [0, 1, 2, 3])
        result = self.memory_run("d-ttl", memory_ttl_tokens=2)
        self.assertEqual(result["body_ids"], base["body_ids"])
        self.assertEqual(result["retained_memory_events"], [2, 3])
        self.assertTrue(result["compactions"])
        self.assertTrue(all(c["reason"] == "ttl" for c in result["compactions"]))
        self.assertEqual(result["compactions"][0]["removed_events"], [0])
        self.assertEqual(result["compactions"][0]["body_position"], 5)
        self.assertEqual(result["compactions"][0]["body_tokens_preserved"], 5)
        base_len = len(self.model.prompt(instruction(self.row) + self.row["question"]))
        self.assertEqual(
            result["final_context_length"],
            base_len + 8 + sum(len(result["events"][i]["memory_ids"]) for i in (2, 3)),
        )

    def test_ttl_and_capacity_compactions_are_distinguishable(self):
        shared = dict(
            memory_capacity_tokens=400,
            memory_compact_to_tokens=100,
            max_event_memory_tokens=256,
            max_output_tokens=40,
        )
        ttl = self.memory_run("d-ttl-only", memory_ttl_tokens=7, **shared)
        self.assertTrue(ttl["compactions"])
        self.assertTrue(all(c["reason"] == "ttl" for c in ttl["compactions"]))
        capacity = self.memory_run("d-cap-only", memory_ttl_tokens=8, **shared)
        self.assertTrue(capacity["compactions"])
        self.assertTrue(all("reason" not in c for c in capacity["compactions"]))

    def test_memory_ttl_resume_is_identical(self):
        self.cfg["experiment"].update(memory_ttl_tokens=2)
        expected = self.controlled(RunStore(self.root / "ttl-expected", {}), arm="all_futures")
        paused = PausableStore(self.root / "ttl-resume", {}, stop_after_calls=14)
        with self.assertRaises(RequestedPause):
            self.controlled(paused, arm="all_futures")
        hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
        actual = self.controlled(RunStore(paused.path, {}, resume=True), arm="all_futures")
        self.assertEqual(actual["body_ids"], expected["body_ids"])
        self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
        self.assertEqual(
            [c["removed_events"] for c in actual["compactions"]],
            [c["removed_events"] for c in expected["compactions"]],
        )
        self.assertTrue(expected["compactions"])
        self.assertTrue(
            all(file_digest(paused.path / "checkpoints" / n) == s for n, s in hashes.items())
        )

    # ---- F ------------------------------------------------------------------
    def forcing(self, force_at=5, answer=9, max_output=16, text=None):
        self.cfg["experiment"].update(
            max_output_tokens=max_output,
            budget_forcing={"force_at_body_tokens": force_at, "answer_tokens": answer},
        )
        text = text if text is not None else "abcde" + chr(126) + self.ANSWER
        return self.scripted(text)

    def test_budget_forcing_inserts_think_end_exactly_and_extracts_answer(self):
        sample = self.forcing()
        store = RunStore(self.root / "force", {})
        result = self.plain(store, sample)
        self.assertEqual(result["forced_think_end_at"], 5)
        self.assertEqual(result["body_ids"][5], 126)
        self.assertEqual(len(result["body_ids"]), 5 + 1 + 9)
        self.assertEqual(result["body_ids"][:5], [ord(c) for c in "abcde"])
        self.assertTrue(result["thinking_complete"])
        self.assertEqual(result["answer_source"], "after_thinking_end")
        self.assertEqual(result["prediction"], "2")
        self.assertTrue(result["correct"])
        starts = sorted(
            json.loads(p.read_text())["payload"]["request"]["body_position"]
            for p in (store.path / "checkpoints").glob("*.json")
            if json.loads(p.read_text())["payload"]["label"].endswith("/scan")
        )
        self.assertEqual(starts, [0, 1, 4, 6, 9, 12])

    def test_budget_forcing_respects_answer_cap(self):
        sample = self.forcing(answer=4, text="abcde" + chr(126) + "xxxxxxxxxxxxx")
        result = self.plain(RunStore(self.root / "force-cap", {}), sample)
        self.assertEqual(len(result["body_ids"]), 5 + 1 + 4)
        self.assertEqual(result["forced_think_end_at"], 5)
        self.assertIsNone(result["prediction"])

    def test_budget_forcing_zero_answer_tokens(self):
        sample = self.forcing(answer=0)
        result = self.plain(RunStore(self.root / "force-zero", {}), sample)
        self.assertEqual(len(result["body_ids"]), 6)
        self.assertEqual(result["body_ids"][-1], 126)

    def test_budget_forcing_not_applied_when_thinking_already_ended(self):
        sample = self.forcing(text="ab" + chr(126) + self.ANSWER)
        result = self.plain(RunStore(self.root / "force-natural", {}), sample)
        self.assertIsNone(result["forced_think_end_at"])
        self.assertEqual(result["body_ids"].count(126), 1)
        self.assertEqual(result["prediction"], "2")

    def test_budget_forcing_keeps_sampling_seeds_for_other_positions(self):
        seen = []
        sample = self.forcing(answer=4, text="abcde" + chr(126) + self.ANSWER)

        def recording(decoder, state, seed):
            seen.append((len(state.generated_ids), seed))
            return sample(decoder, state, seed)

        with patch.object(StreamDecoder, "sample", recording):
            result = run_condition(
                self.model,
                RunStore(self.root / "force-seed", {}),
                self.row,
                self.cfg,
                "test",
                "plain_ar",
                lambda _: None,
            )
        self.assertIsNotNone(result["forced_think_end_at"])
        seed = derived_seed(self.cfg["experiment"]["seed"], "test", self.row["id"])
        positions = [p for p, _ in seen]
        self.assertNotIn(5, positions)
        self.assertTrue(any(p > 5 for p in positions))
        self.assertEqual(positions, [i for i in range(len(result["body_ids"])) if i != 5])
        for position, got in seen:
            self.assertEqual(got, derived_seed(seed, "body", position), position)

    def test_budget_forcing_resume_is_identical(self):
        sample = self.forcing()
        expected = self.plain(RunStore(self.root / "f-expected", {}), sample)
        for stop in (3, 4, 5, 6):
            paused = PausableStore(self.root / f"f-resume-{stop}", {}, stop_after_calls=stop)
            with self.assertRaises(RequestedPause):
                self.plain(paused, sample)
            hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
            actual = self.plain(RunStore(paused.path, {}, resume=True), sample)
            self.assertEqual(actual["body_ids"], expected["body_ids"])
            self.assertEqual(actual["forced_think_end_at"], 5)
            self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
            self.assertEqual(actual["prediction"], expected["prediction"])
            self.assertTrue(
                all(file_digest(paused.path / "checkpoints" / n) == s for n, s in hashes.items())
            )

    # ---- audit --------------------------------------------------------------
    def audited(self, arm, patches):
        from lost_tokens.audit import audit

        self.row["task"] = "fixture"
        cfg = copy.deepcopy(self.cfg)
        cfg["experiment"]["arms"] = [arm]
        cfg["datasets"] = [{"name": "fixture"}]
        cfg["smoke"] = {"tasks": ["fixture"], "cases_per_task": 1}
        split = {"tasks": {"fixture": {"development": [self.row]}}}
        identity = {"spec": cfg, "source": {}, "split_sha256": digest(split), "mode": "smoke"}
        store = RunStore(self.root / ("audit-" + arm), identity)
        atomic_json(store.path / "split.json", split)
        atomic_json(store.path / "resolved-config.json", cfg)
        from contextlib import ExitStack

        with ExitStack() as stack:
            for patcher in patches:
                stack.enter_context(patcher)
            result = run_condition(
                self.model, store, self.row, cfg, "smoke/fixture", arm, lambda _: None
            )
        store.call(f"smoke/fixture/cpu/{arm}/complete", {}, lambda: result)
        return audit(store.path, partial=True, model=self.model), result

    def test_audit_passes_with_forcing(self):
        sample = self.forcing()
        reviewed, result = self.audited("plain_ar", [patch.object(StreamDecoder, "sample", sample)])
        self.assertEqual(reviewed["completed_conditions"], 1)
        self.assertEqual(result["forced_think_end_at"], 5)

    def test_audit_passes_with_a_b_and_ttl(self):
        self.cfg["experiment"].update(
            memory_ttl_tokens=2, max_memory_events=3, min_branch_body_tokens=2
        )
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            ],
        )
        self.assertEqual(reviewed["events"], len(result["events"]))
        self.assertEqual(sum(bool(e["memory_ids"]) for e in result["events"]), 3)
        self.assertTrue(any(c.get("reason") == "ttl" for c in result["compactions"]))

    def test_audit_detects_tampered_compaction_summary(self):
        self.cfg["experiment"].update(
            memory_ttl_tokens=2, max_memory_events=3, min_branch_body_tokens=2
        )
        patches = [
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
        ]
        from lost_tokens.audit import audit

        reviewed, result = self.audited("all_futures", patches)
        self.assertTrue(result["compactions"])
        path = next(
            p
            for p in (self.root / "audit-all_futures" / "checkpoints").glob("*.json")
            if json.loads(p.read_text())["payload"]["label"]
            == "smoke/fixture/" + self.row["id"] + "/all_futures/complete"
        )
        original = path.read_text()
        for field, value in (
            ("removed_events", [99]),
            ("body_tokens_preserved", 10**6),
            ("body_position", 10**6),
            ("remaining_context_length", 10**6),
            ("reason", "capacity"),
        ):
            item = json.loads(original)
            item["payload"]["result"]["compactions"][0][field] = value
            item["sha256"] = digest(item["payload"])
            atomic_json(path, item)
            with self.assertRaises(AssertionError, msg=field):
                audit(path.parent.parent, partial=True, model=self.model)
        path.write_text(original)
        audit(path.parent.parent, partial=True, model=self.model)

    def test_budget_forcing_supported_for_all_arms(self):
        self.forcing()
        for arm in ("reference_only", "all_futures", "filtered_futures"):
            with (
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
                patch("lost_tokens.recurrent_memory.compare_rollouts", self.keep),
            ):
                result = run_condition(
                    self.model,
                    RunStore(self.root / ("bf-" + arm), {}),
                    self.row,
                    self.cfg,
                    "test",
                    arm,
                    lambda _: None,
                )
            self.assertEqual(result["forced_think_end_at"], 5)
            self.assertEqual(result["body_ids"][5], 126)
            self.assertTrue(all(e["body_position"] < 5 for e in result["events"]))
        spec = load_spec()
        spec["experiment"]["budget_forcing"] = {"force_at_body_tokens": 10, "answer_tokens": 5}
        spec["experiment"]["arms"] = ["plain_ar", "filtered_futures"]
        path = self.root / "bf-spec.json"
        path.write_text(json.dumps(spec))
        load_spec(path)
        spec["experiment"]["arms"] = ["plain_ar"]
        path.write_text(json.dumps(spec))
        load_spec(path)

    def test_audit_passes_with_knobs_off(self):
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            ],
        )
        self.assertEqual(reviewed["events"], 4)

    # ---- validation ---------------------------------------------------------
    def test_config_validation_rejects_bad_knobs(self):
        good = {"force_at_body_tokens": 10, "answer_tokens": 5}
        bad = [
            ("max_memory_events", 0),
            ("max_memory_events", True),
            ("max_memory_events", 1.5),
            ("min_branch_body_tokens", -1),
            ("min_branch_body_tokens", True),
            ("memory_ttl_tokens", 0),
            ("memory_ttl_tokens", "3"),
            ("budget_forcing", 5),
            ("budget_forcing", {"force_at_body_tokens": 10}),
            ("budget_forcing", {**good, "extra": 1}),
            ("budget_forcing", {**good, "force_at_body_tokens": 0}),
            ("budget_forcing", {**good, "answer_tokens": -1}),
            ("budget_forcing", {**good, "answer_tokens": True}),
            ("budget_forcing", {"force_at_body_tokens": 32768, "answer_tokens": 0}),
            ("budget_forcing", {"force_at_body_tokens": 100, "answer_tokens": 32668}),
        ]
        for key, value in bad:
            spec = load_spec()
            spec["experiment"][key] = value
            path = self.root / "bad-knob.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError, msg=f"{key}={value!r}"):
                load_spec(path)
        for key, value in (
            ("max_memory_events", 1),
            ("max_memory_events", None),
            ("min_branch_body_tokens", 0),
            ("memory_ttl_tokens", 1),
            ("budget_forcing", None),
            ("budget_forcing", {"force_at_body_tokens": 100, "answer_tokens": 32667}),
        ):
            spec = load_spec()
            spec["experiment"][key] = value
            if key == "budget_forcing":
                spec["experiment"]["arms"] = ["plain_ar"]
            path = self.root / "good-knob.json"
            path.write_text(json.dumps(spec))
            load_spec(path)

    def test_runtime_override_of_max_output_revalidates_forcing(self):
        self.cfg["experiment"].update(
            max_output_tokens=8, budget_forcing={"force_at_body_tokens": 8, "answer_tokens": 1}
        )
        with self.assertRaises(ValueError):
            self.plain(RunStore(self.root / "force-bad", {}))


if __name__ == "__main__":
    unittest.main()
