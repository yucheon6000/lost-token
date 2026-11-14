import copy
import json
from pathlib import Path
import tempfile
import unittest

from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.core import atomic_json, file_digest
from lost_tokens import frozen_baseline as frozen


class FrozenBaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        spec = runtime_spec(load_spec(), self.work)
        self.study = {
            "branch": "tester-base-2026-11-15",
            "code_commit": "a" * 40,
            "spec": spec,
            "task_specs": {"aime25": spec},
            "counts": {"aime25": 2},
            "runs": {"aime25": "base"},
            "cohort_version": "test-v1",
            "cohort_manifest_sha256": "b" * 64,
            "hardware_profile": "test-profile",
            "source": {
                k: "c" * 64
                for k in (
                    "lost_tokens/core.py",
                    "lost_tokens/math_scoring.py",
                    "lost_tokens/data.py",
                    "lost_tokens/recurrent_memory.py",
                )
            },
            "environment": {"runtime": {"packages": {"torch": "test"}}, "scoring_packages": {}},
        }
        self.make_run("base", "baseline", {"a": True, "b": False})
        self.target = self.work / "baseline-reference.json"

    def make_run(self, name, arm, scores):
        run = self.work / "outputs" / name
        worker = arm + "-worker0"
        atomic_json(
            run / "plan.json",
            {
                "source": self.study["source"],
                "arms": [arm],
                "workers": [{"name": worker, "arm": arm, "split": "configs/split.json"}],
            },
        )
        atomic_json(
            run / "configs/split.json",
            {"tasks": {"aime25": {"evaluation": [{"id": k} for k in scores]}}},
        )
        atomic_json(run / "schedule.json", {arm: {"start_epoch": 100, "deadline_epoch": None}})
        atomic_json(run / f"{arm}-complete.json", {"at": "1970-01-01T00:02:00+00:00"})
        atomic_json(run / "status.json", {"state": "complete", "audits_passed": True})
        for ident, correct in scores.items():
            atomic_json(
                run / "workers" / worker / "outcomes/aime25" / f"{ident}.json",
                {
                    "task": "aime25",
                    "id": ident,
                    "correct": correct,
                    "finished_epoch": 110,
                },
            )
        return run

    def test_freeze_then_reuse_for_changed_ours_without_touching_baseline(self):
        reference = frozen.freeze(self.study, self.work, self.target)
        before = file_digest(self.target)
        changed = copy.deepcopy(self.study)
        changed["source"]["lost_tokens/recurrent_memory.py"] = "d" * 64
        changed["spec"]["experiment"]["selection"] = "argmax"
        frozen.read_reference(self.target, frozen.conditions(changed))
        ours = self.make_run("ours", "ours", {"a": False, "b": True})
        paired = frozen.compare(reference, ours, "aime25")
        self.assertEqual((paired["n"], paired["wins"], paired["losses"]), (2, 1, 1))
        self.assertEqual(frozen.score(reference, "aime25"), {"n": 2, "correct": 1})
        self.assertEqual(file_digest(self.target), before)
        self.assertEqual(frozen.freeze(self.study, self.work, self.target), reference)

    def test_changed_sampling_or_scorer_and_modified_reference_are_rejected(self):
        frozen.freeze(self.study, self.work, self.target)
        for key in ("sampling", "scorer"):
            changed = copy.deepcopy(self.study)
            if key == "sampling":
                changed["spec"]["experiment"]["temperature"] = 0.9
            else:
                changed["source"]["lost_tokens/math_scoring.py"] = "e" * 64
            with self.assertRaises(ValueError):
                frozen.read_reference(self.target, frozen.conditions(changed))
        saved = json.loads(self.target.read_text())
        saved["payload"]["outcomes"]["aime25"][0]["correct"] = False
        atomic_json(self.target, saved)
        with self.assertRaises(ValueError):
            frozen.read_reference(self.target)

    def test_partial_baseline_is_not_frozen_and_unmatched_ids_are_rejected(self):
        path = self.work / "outputs/base/workers/baseline-worker0/outcomes/aime25/b.json"
        original = path.read_bytes()
        path.unlink()
        self.assertIsNone(frozen.freeze(self.study, self.work, self.target))
        self.assertFalse(self.target.exists())
        path.write_bytes(original)
        reference = frozen.freeze(self.study, self.work, self.target)
        other = self.make_run("other", "ours", {"outside": True})
        with self.assertRaises(ValueError):
            frozen.compare(reference, other, "aime25")
