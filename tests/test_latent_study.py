"""Full-suite coverage, separate preflights, and sealed AR reference integrity."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("latent_study", ROOT / "scripts/run_latent_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class LatentStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_required_scope_and_report_never_include_preflight_in_scores(self):
        self.assertEqual(set(study.TASKS), {"aime25", "hmmt25", "gpqa", "gsm8k", "math500", "mmlu"})
        jobs = []
        cohort = {}
        for task in study.TASKS:
            cohort[task] = {"n": 100}
            for mode in ["ar", "selar"]:
                path = self.root / task / mode
                out = path / "outcomes"
                out.mkdir(parents=True)
                row = {
                    "id": task + "-one",
                    "task": task,
                    "mode": mode,
                    "correct": mode == "selar",
                    "prediction": "A",
                    "soft_tokens": 1 if mode == "selar" else 0,
                    "body_tokens": 10,
                }
                (out / "one.json").write_text(json.dumps(row))
                jobs.append(
                    {
                        "stage": "evaluation",
                        "task": task,
                        "mode": mode,
                        "state": "running",
                        "workers": [{"path": str(path)}],
                    }
                )
        path = self.root / "preflight"
        out = path / "outcomes"
        out.mkdir(parents=True)
        (out / "extra.json").write_text(
            json.dumps(
                {
                    "id": "preflight-only",
                    "task": "gsm8k",
                    "mode": "selar",
                    "correct": True,
                    "prediction": "9",
                    "soft_tokens": 2,
                    "body_tokens": 10,
                }
            )
        )
        jobs.append(
            {
                "stage": "preflight",
                "task": "gsm8k",
                "mode": "selar",
                "state": "complete",
                "n_required": 1,
                "workers": [{"path": str(path)}],
            }
        )
        state = {"state": "running", "jobs": jobs}
        study.export(self.root, {"cohort": cohort}, state)
        self.assertEqual(jobs[1]["n"], 1)
        self.assertEqual(jobs[-1]["n"], 1)
        self.assertIn("pending", (self.root / "results.md").read_text())

    def test_sealed_baseline_is_not_overwritten(self):
        path = self.root / "worker"
        out = path / "outcomes"
        out.mkdir(parents=True)
        row = {"id": "one", "task": "gsm8k", "mode": "ar", "correct": True}
        (out / "one.json").write_text(json.dumps(row))
        job = {
            "task": "gsm8k",
            "mode": "ar",
            "n_required": 1,
            "correct": 1,
            "started_at": "start",
            "finished_at": "end",
            "workers": [{"path": str(path)}],
        }
        manifest = {
            "source": {},
            "code_commit": "commit",
            "config": {},
            "environment": {},
            "cohort": {"gsm8k": {"manifest_sha256": "manifest", "ids": ["one"]}},
        }
        study.seal_baseline(self.root, job, manifest)
        saved = (self.root / "baselines/gsm8k.json").read_bytes()
        study.seal_baseline(self.root, job, manifest)
        self.assertEqual((self.root / "baselines/gsm8k.json").read_bytes(), saved)
        job["correct"] = 0
        with self.assertRaisesRegex(ValueError, "Sealed AR"):
            study.seal_baseline(self.root, job, manifest)


if __name__ == "__main__":
    unittest.main()
