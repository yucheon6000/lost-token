"""Cross-event deduplication preserves replay, audits, and selected continuations."""

import copy
import json
import unittest
from unittest.mock import patch

from lost_tokens.audit import audit
from lost_tokens.config import validate_spec
from lost_tokens.core import RunStore, atomic_json, digest, file_digest
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.recurrent_memory import StreamDecoder, run_condition
import test_knobs as knobs
import test_recurrent_memory as base


class Encoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(texts)
        return [[1.0, 0.0] if t.startswith("A") else [0.0, 1.0] for t in texts], len(texts)


class RecentAlternativeTests(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    audited = knobs.KnobTests.audited

    def setUp(self):
        base.RecurrentTests.setUp(self)
        self.cfg["experiment"].update(
            max_output_tokens=32,
            branch_tokens=4,
            min_branch_interval_tokens=5,
            max_branch_candidates=2,
            memory_format="original_unchosen",
            min_branch_entropy=1.3,
        )
        self.cfg["similarity"]["recent_alternatives_window"] = 4
        self.model.semantic_encoder = Encoder()

    @staticmethod
    def eligible(decoder, state):
        return {**base.RecurrentTests.eligible(decoder, state), "entropy": 1.4}

    def patches(self):
        return [
            patch.object(StreamDecoder, "candidates", self.eligible),
            patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
        ]

    def run_case(self, store):
        candidates, sample = self.patches()
        with candidates, sample:
            return run_condition(
                self.model, store, self.row, self.cfg, "test", "filtered_futures", lambda _: None
            )

    def test_duplicates_do_not_inject_memory_and_original_still_commits(self):
        result = self.run_case(RunStore(self.root / "duplicates", {}))
        self.assertGreater(len(result["events"]), 3)
        self.assertEqual(result["events"][0]["retained_ranks"], [2])
        for event in result["events"][1:]:
            self.assertEqual(event["retained_ranks"], [])
            self.assertEqual(event["memory_ids"], [])
            self.assertEqual(event["committed_ids"], event["previews"][0]["ids"])
            self.assertEqual(event["similarity"]["recent_alternatives"][0]["event"], 0)
        self.assertTrue(all(len(call) == 2 for call in self.model.semantic_encoder.calls))

    def test_expired_memory_is_not_used_for_deduplication(self):
        self.cfg["experiment"]["memory_ttl_tokens"] = 1
        result = self.run_case(RunStore(self.root / "expired", {}))
        self.assertTrue(result["compactions"])
        self.assertTrue(all(e["retained_ranks"] == [2] for e in result["events"]))
        self.assertTrue(all(e["similarity"]["recent_alternatives"] == [] for e in result["events"]))

    def test_disabled_window_keeps_original_filter(self):
        self.cfg["similarity"]["recent_alternatives_window"] = 0
        result = self.run_case(RunStore(self.root / "disabled", {}))
        self.assertTrue(all(e["retained_ranks"] == [2] for e in result["events"]))
        self.assertTrue(all("recent_decisions" not in e["similarity"] for e in result["events"]))

    def test_compacted_memory_is_not_used_for_deduplication(self):
        self.cfg["experiment"].update(
            memory_capacity_tokens=128, max_event_memory_tokens=128, memory_compact_to_tokens=1
        )
        result = self.run_case(RunStore(self.root / "compacted", {}))
        self.assertTrue(result["compactions"])
        self.assertTrue(all(e["retained_ranks"] == [2] for e in result["events"]))
        self.assertTrue(all(e["similarity"]["recent_alternatives"] == [] for e in result["events"]))

    def test_audit_passes_and_rejects_tampered_history_reference(self):
        reviewed, _ = self.audited("filtered_futures", self.patches())
        self.assertEqual(reviewed["completed_conditions"], 1)
        run = self.root / "audit-filtered_futures"
        for path in (run / "checkpoints").glob("*.json"):
            item = json.loads(path.read_text())
            request = item["payload"]["request"]
            if item["payload"]["label"].endswith("/cosine") and request["recent_alternatives"]:
                request["recent_alternatives"][0]["event"] = 99
                item["sha256"] = digest(item["payload"])
                atomic_json(path, item)
                break
        else:
            self.fail("No history-bearing cosine checkpoint")
        with self.assertRaises(AssertionError):
            audit(run, partial=True, model=self.model)

    def test_interrupted_resume_preserves_memory_and_checkpoints(self):
        expected = self.run_case(RunStore(self.root / "expected", {}))
        for stop in (6, 9, 12):
            paused = PausableStore(self.root / f"resume-{stop}", {}, stop_after_calls=stop)
            with self.assertRaises(RequestedPause):
                self.run_case(paused)
            hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
            actual = self.run_case(RunStore(paused.path, {}, resume=True))
            self.assertEqual(knobs.strip_time(actual), knobs.strip_time(expected))
            self.assertTrue(
                all(file_digest(paused.path / "checkpoints" / n) == h for n, h in hashes.items())
            )

    def test_recent_window_config_rejects_invalid_values(self):
        for value in (-1, True, 1.5, "4", None):
            spec = copy.deepcopy(self.cfg)
            spec["similarity"]["recent_alternatives_window"] = value
            with self.assertRaisesRegex(ValueError, "recent_alternatives_window"):
                validate_spec(spec)
