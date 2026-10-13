"""Repeated seeds remain distinct, paired, deadline-filtered observations."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


path = Path(__file__).resolve().parents[1] / "scripts/comparison_report.py"
spec = importlib.util.spec_from_file_location("comparison_report", path)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class ComparisonReportingTests(unittest.TestCase):
    def test_pairs_same_seed_and_question_and_excludes_late_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = []
            for seed in (1, 2):
                for arm in ("baseline", "ours"):
                    run = root / f"{arm}-{seed}"
                    out = run / "workers/worker0/outcomes/aime25"
                    out.mkdir(parents=True)
                    plan = {
                        "arms": [arm],
                        "workers": [{"name": "worker0", "arm": arm}],
                        "counts": {"aime25": 1},
                    }
                    (run / "plan.json").write_text(json.dumps(plan))
                    (run / "schedule.json").write_text(json.dumps({arm: {"deadline_epoch": 100}}))
                    row = {
                        "id": "same-question",
                        "task": "aime25",
                        "correct": (seed == 1) == (arm == "ours"),
                        "finished_epoch": 99,
                        "thinking_complete": True,
                        "body_tokens": 10,
                        "events": 0,
                        "seconds": 1,
                    }
                    (out / "one.json").write_text(json.dumps(row))
                    (out / "late.json").write_text(
                        json.dumps({**row, "id": "late", "finished_epoch": 101})
                    )
                    runs.append({"name": run.name, "arm": arm, "seed": seed, "path": str(run)})
            (root / "comparison.json").write_text(
                json.dumps(
                    {"state": "running", "identity": {"benchmarks": ["aime25"]}, "runs": runs}
                )
            )
            result = reporter.report_comparison(root)
            self.assertEqual(result["paired"]["all"]["n"], 2)
            self.assertEqual(result["paired"]["all"]["wins"], 1)
            self.assertEqual(result["paired"]["all"]["losses"], 1)
            self.assertEqual(result["own"]["baseline"]["all"]["unique_questions"], 1)
            self.assertEqual(result["own"]["ours"]["all"]["seeds"], [1, 2])
            self.assertEqual(result["per_seed"]["1"]["paired"]["all"]["n"], 1)
            self.assertTrue(result["per_seed"]["1"]["full_cohort"])
