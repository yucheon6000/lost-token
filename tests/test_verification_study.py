"""Guard against confounded controls and misleading partial-cohort comparisons."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import digest, file_digest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verification_study", ROOT / "scripts/run_verification_study.py"
)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class VerificationStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_frozen_pairs_only_change_verification_and_keep_original_sampling(self):
        pipeline = json.loads((ROOT / "configs/verification-study.json").read_text())
        self.assertEqual(set(pipeline["condition_order"]), {"control", "verification"})
        self.assertEqual(
            set(pipeline["benchmarks"]), {"aime25", "hmmt25", "gpqa", "gsm8k", "math500", "mmlu"}
        )
        self.assertEqual(pipeline["required_benchmarks"], pipeline["benchmarks"])
        self.assertEqual(pipeline["cohort"], "full-v1")
        for task, pair in pipeline["configs_by_task"].items():
            with self.subTest(task=task):
                study.validate_pair(ROOT / pair["control"], ROOT / pair["verification"])
                cfg = load_spec(ROOT / pair["verification"])
                self.assertEqual(cfg["experiment"]["max_output_tokens"], 32768)
                self.assertEqual(cfg["experiment"]["seed"], 95021)

    def test_changed_sampling_or_enabled_control_is_rejected(self):
        base = load_spec(ROOT / "configs/vllm-argmax.json")
        verify = load_spec(ROOT / "configs/verification-argmax.json")
        a, b = self.root / "control.json", self.root / "verify.json"
        a.write_text(json.dumps(base))
        verify["experiment"]["temperature"] = 0.8
        b.write_text(json.dumps(verify))
        with self.assertRaises(ValueError):
            study.validate_pair(a, b)
        verify["experiment"]["temperature"] = base["experiment"]["temperature"]
        b.write_text(json.dumps(verify))
        base["experiment"]["disagreement_verification"] = copy.deepcopy(
            verify["experiment"]["disagreement_verification"]
        )
        a.write_text(json.dumps(base))
        with self.assertRaises(ValueError):
            study.validate_pair(a, b)

    def test_partial_report_compares_only_identical_completed_ids(self):
        run = self.root / "run"
        out = run / "workers/ours-worker0/outcomes/task"
        out.mkdir(parents=True)
        (out / "one.json").write_text(
            json.dumps({"id": "one", "task": "task", "arm": "ours", "correct": True})
        )
        manifest = {
            "cohort": {"task": {"ids": ["one", "two"]}},
            "comparison": {
                "task": {"baseline": {"one": {"correct": False}, "two": {"correct": True}}}
            },
        }
        state = {
            "state": "running",
            "jobs": [
                {
                    "task": "task",
                    "variant": "verification",
                    "state": "running",
                    "run": str(run),
                    "n_required": 2,
                }
            ],
        }
        study.export(self.root, manifest, state)
        job = state["jobs"][0]
        self.assertEqual(
            (job["n"], job["correct"], job["baseline_correct_on_completed"]), (1, 1, 0)
        )
        self.assertEqual((job["wins_baseline"], job["losses_baseline"]), (1, 0))
        self.assertIn("task: 1/2", (self.root / "results.md").read_text())
        (out / "rogue.json").write_text(
            json.dumps({"id": "rogue", "task": "task", "arm": "ours", "correct": True})
        )
        with self.assertRaises(ValueError):
            study.export(self.root, manifest, state)

    def test_whole_suite_rejects_silent_truncation_and_missing_full_manifest(self):
        pipeline = json.loads((ROOT / "configs/verification-study.json").read_text())
        p = self.root / "pipeline.json"
        args = SimpleNamespace(pipeline=p, cohort_manifest=None)
        p.write_text(json.dumps(pipeline))
        with patch.object(study, "git", return_value=""):
            with self.assertRaisesRegex(ValueError, "requires the committed full-v1"):
                study.initialize(args)
            pipeline["benchmarks"] = ["aime25", "hmmt25", "gpqa"]
            p.write_text(json.dumps(pipeline))
            with self.assertRaisesRegex(ValueError, "must not be truncated"):
                study.initialize(args)

    def test_full_cohort_uses_exact_stored_order_and_rejects_missing_or_changed_rows(self):
        rows = [{"id": "second", "question": "b"}, {"id": "first", "question": "a"}]
        ids = [r["id"] for r in rows]
        source = {"lost_tokens/data.py": "data", "lost_tokens/datasets.json": "pins"}
        full = {
            "version": "full-v1",
            "source": source,
            "datasets": {
                "task": {
                    "ids": ids,
                    "n": 2,
                    "full_n": 2,
                    "ids_sha256": digest(ids),
                    "rows_sha256": digest(rows),
                }
            },
        }
        p = self.root / "full.json"
        p.write_text(json.dumps(full))
        original = file_digest(p)
        with (
            patch.object(study.shared, "verify_cohort"),
            patch.object(study, "source_fingerprint", return_value=source),
            patch.object(study, "load_prepared", return_value=list(reversed(rows))) as prepared,
        ):
            got, path, sha, version = study.frozen_cohort(self.root, {}, "task", self.root, p)
            self.assertEqual(got, ids)
            self.assertEqual(path, p)
            self.assertEqual((sha, version), (original, "full-v1"))
            prepared.return_value = rows[:1]
            with self.assertRaisesRegex(ValueError, "coverage differ"):
                study.frozen_cohort(self.root, {}, "task", self.root, p)
            prepared.return_value = [{**r, "question": "changed"} for r in rows]
            with self.assertRaisesRegex(ValueError, "coverage differ"):
                study.frozen_cohort(self.root, {}, "task", self.root, p)
        self.assertEqual(file_digest(p), original)

    def test_reuse_preserves_audited_original_and_rejects_changed_outcomes(self):
        parent, run = self.root / "parent", self.root / "run"
        parent.mkdir()
        out = run / "workers/ours-worker0/outcomes/task"
        out.mkdir(parents=True)
        row = {"id": "one", "task": "task", "arm": "ours", "correct": True}
        path = out / "one.json"
        path.write_text(json.dumps(row))
        cfg = ROOT / "configs/vllm-argmax.json"
        original = {
            "task": "task",
            "variant": "control",
            "arm": "ours",
            "state": "complete",
            "audits_passed": True,
            "finished_at": "2026-01-01T00:00:00+00:00",
            "run": str(run),
            "config": str(cfg),
            "outcomes_sha256": digest([row]),
            "phase_wall_seconds": 123.0,
        }
        (parent / "manifest.json").write_text(
            json.dumps({"source": {}, "gpus": "0", "code_commit": "original"})
        )
        (parent / "status.json").write_text(json.dumps({"state": "complete", "jobs": [original]}))
        (run / "status.json").write_text(json.dumps({"state": "complete", "audits_passed": True}))
        (run / "plan.json").write_text(
            json.dumps({"source": {}, "arms": ["ours"], "gpus": ["0"], "seconds_per_arm": None})
        )
        (run / "schedule.json").write_text("{}")
        job = {
            "task": "task",
            "variant": "control",
            "config": str(cfg),
            "run": str(self.root / "new-run"),
        }
        inputs = study.reuse_completed(parent, [job], {"task": {"ids": ["one"]}}, {}, "0")
        self.assertEqual(job["run"], str(run))
        self.assertEqual(job["phase_wall_seconds"], 123.0)
        self.assertEqual(job["reused_from"]["code_commit"], "original")
        self.assertIn(str(run / "schedule.json"), inputs)
        path.write_text(json.dumps({**row, "correct": False}))
        with self.assertRaisesRegex(ValueError, "outcomes differ"):
            study.reuse_completed(parent, [job], {"task": {"ids": ["one"]}}, {}, "0")


if __name__ == "__main__":
    unittest.main()
