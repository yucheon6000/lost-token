import copy
import importlib.util
from pathlib import Path
import unittest

from lost_tokens.core import digest

spec = importlib.util.spec_from_file_location(
    "consistency", Path(__file__).parents[1] / "scripts/check_inference_consistency.py"
)
consistency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consistency)


class ConsistencyDiagnosticTests(unittest.TestCase):
    def test_engine_stop_token_variants_and_corrupted_outputs(self):
        for actual in ([1, 2], [1, 2, 99]):
            self.assertTrue(consistency.engine_tokens_match(actual, [1, 2], {99}))
        self.assertTrue(consistency.engine_tokens_match([1, 2], [1, 2, 99], {99}))
        for actual in ([1], [1, 3], [1, 2, 7], [1, 2, 99, 99]):
            self.assertFalse(consistency.engine_tokens_match(actual, [1, 2], {99}))

    def test_incremental_replay_does_not_emit_chat_prompt_stop_tokens(self):
        self.assertEqual(
            consistency.incremental_tail_length({"ids": list(range(200)), "body_ids": [7]}), 1
        )
        self.assertEqual(
            consistency.incremental_tail_length(
                {"ids": list(range(200)), "body_ids": list(range(70))}
            ),
            64,
        )

    def test_sampling_is_order_independent_and_task_specific(self):
        ids = [str(i) for i in range(100)]
        selected = consistency.sample_ids(ids, "a", 10)
        self.assertEqual(selected, consistency.sample_ids(ids[::-1], "a", 10))
        self.assertNotEqual(selected, consistency.sample_ids(ids, "b", 10))
        self.assertEqual(len(set(selected)), 10)
        with self.assertRaises(ValueError):
            consistency.sample_ids(ids, "a", 101)
        with self.assertRaises(ValueError):
            consistency.sample_ids(ids + ["1"], "a", 10)

    @staticmethod
    def fixture():
        base = [100]
        first = {
            "body_position": 1,
            "root_sha256": digest([100, 1]),
            "root_length": 2,
            "memory_ids": [90, 91],
            "continuation_root_sha256": digest([100, 1, 90, 91]),
            "committed_ids": [2],
            "after_commit_sha256": digest([100, 1, 90, 91, 2]),
        }
        second = {
            "body_position": 3,
            "root_sha256": digest([100, 1, 2, 3]),
            "root_length": 4,
            "memory_ids": [],
            "continuation_root_sha256": digest([100, 1, 2, 3]),
            "committed_ids": [4],
            "after_commit_sha256": digest([100, 1, 2, 3, 4]),
        }
        result = {
            "events": [first, second],
            "body_ids": [1, 2, 3, 4, 5],
            "compactions": [
                {"body_position": 3, "removed_events": [0], "remaining_context_length": 4}
            ],
            "final_context_sha256": digest([100, 1, 2, 3, 4, 5]),
        }
        return {"conditions": {"filtered_futures": result}}, base, {"memory_compact_to_tokens": 0}

    def test_reconstruction_compacts_before_fork_without_removing_body(self):
        case, base, exp = self.fixture()
        original = copy.deepcopy(case)
        probes = consistency.reconstruct(case, base, exp)
        self.assertEqual([p["kind"] for p in probes], ["first", "compaction", "middle"])
        self.assertEqual(probes[1]["before_compaction_ids"], [100, 1, 90, 91, 2, 3])
        self.assertEqual(probes[1]["ids"], [100, 1, 2, 3])
        self.assertEqual(probes[1]["body_ids"], [1, 2, 3])
        self.assertEqual(case, original)

    def test_reconstruction_rejects_corrupted_event_or_final_context(self):
        for location in ("event", "final"):
            case, base, exp = self.fixture()
            r = case["conditions"]["filtered_futures"]
            if location == "event":
                r["events"][1]["root_sha256"] = "wrong"
            else:
                r["final_context_sha256"] = "wrong"
            with self.assertRaises(AssertionError):
                consistency.reconstruct(case, base, exp)
