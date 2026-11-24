"""Frozen reference reuse refuses altered seeds, coverage, results or runtime."""

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from lost_tokens.core import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("em_study", ROOT / "scripts/run_eminf_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class StudyTests(unittest.TestCase):
    def test_baseline_compatibility_checks_every_old_generative_component(self):
        cfg = {"model": {"name": "same"}, "experiment": {"seed": 17}, "latent_reasoning": {}}
        runtime = {"packages": {"torch": "same"}}
        source = {
            "lost_tokens/core.py": "core",
            "lost_tokens/recurrent_memory.py": "decoder",
            "lost_tokens/config.py": "old",
        }
        parent = {
            "config": cfg,
            "environment": {"runtime": runtime},
            "source": source,
            "inputs": {"/repo/uv.lock": "lock"},
            "gpus": "0",
        }
        new = {**cfg, "em_inf": {"n_grad_steps": 3}}
        study.compatible_baseline(
            parent,
            new,
            {**source, "lost_tokens/config.py": "new", "lost_tokens/eminf.py": "new"},
            runtime,
            "0",
            "lock",
        )
        for changed in (
            {**new, "experiment": {"seed": 18}},
            {**new, "model": {"name": "different"}},
        ):
            with self.assertRaises(ValueError):
                study.compatible_baseline(parent, changed, source, runtime, "0", "lock")
        for change in (
            {**source, "lost_tokens/core.py": "bad"},
            {**source, "lost_tokens/recurrent_memory.py": "bad"},
        ):
            with self.assertRaises(ValueError):
                study.compatible_baseline(parent, new, change, runtime, "0", "lock")
        with self.assertRaises(ValueError):
            study.compatible_baseline(parent, new, source, {}, "0", "lock")
        with self.assertRaises(ValueError):
            study.compatible_baseline(parent, new, source, runtime, "0", "different")

    def test_reference_requires_seal_complete_coverage_and_original_audits(self):
        row = {"id": "one", "task": "gpqa", "mode": "ar", "correct": True, "audits_passed": True}
        cohort = {"n": 1, "ids": ["one"], "manifest_sha256": "cohort"}
        parent = {"source": {}, "code_commit": "commit", "config": {}, "environment": {}}
        payload = {
            **parent,
            "task": "gpqa",
            "n": 1,
            "correct": 1,
            "outcomes": [row],
            "cohort_ids_sha256": digest(["one"]),
            "cohort_manifest_sha256": "cohort",
        }
        item = {"payload": payload, "sha256": digest(payload)}
        job = {"state": "complete", "audits_passed": True, "outcomes_sha256": digest([row])}
        self.assertEqual(study.validate_reference(item, "gpqa", cohort, job, parent), payload)
        for update in ({"correct": 0}, {"outcomes": []}, {"code_commit": "changed"}):
            corrupted = {"payload": {**payload, **update}}
            corrupted["sha256"] = digest(corrupted["payload"])
            with self.assertRaises(ValueError):
                study.validate_reference(corrupted, "gpqa", cohort, job, parent)
        with self.assertRaises(ValueError):
            study.validate_reference(item, "gpqa", cohort, {**job, "state": "running"}, parent)

    def test_all_six_full_tasks_and_preflights_are_separate(self):
        self.assertEqual(set(study.TASKS), {"aime25", "hmmt25", "gpqa", "gsm8k", "math500", "mmlu"})
        with tempfile.TemporaryDirectory(dir="temp/diagnostics") as tmp:
            root = Path(tmp)
            jobs = []
            baseline = {}
            for task in study.TASKS:
                path = root / task
                out = path / "outcomes"
                row = {
                    "id": task + "-one",
                    "task": task,
                    "mode": "eminf",
                    "correct": False,
                    "prediction": "B",
                    "optimized_tokens": 3,
                    "body_tokens": 10,
                }
                atomic_json(out / "one.json", row)
                jobs.append(
                    {
                        "task": task,
                        "stage": "evaluation",
                        "mode": "eminf",
                        "state": "complete",
                        "workers": [{"path": str(path)}],
                    }
                )
                baseline[task] = {
                    "n": 1,
                    "correct": 1,
                    "outcomes": [{"id": row["id"], "correct": True}],
                }
            path = root / "preflight"
            atomic_json(
                path / "outcomes/extra.json",
                {
                    "id": "diagnostic",
                    "task": "gsm8k",
                    "mode": "eminf",
                    "correct": True,
                    "prediction": "A",
                    "optimized_tokens": 1,
                    "body_tokens": 10,
                },
            )
            jobs.append(
                {
                    "task": "gsm8k",
                    "stage": "preflight",
                    "mode": "eminf",
                    "state": "complete",
                    "n_required": 1,
                    "workers": [{"path": str(path)}],
                }
            )
            study.export(root, {"baseline": baseline}, {"state": "complete", "jobs": jobs})
            self.assertEqual(jobs[0]["n"], 1)
            self.assertEqual(jobs[0]["losses"], 1)
            self.assertEqual(jobs[-1]["n"], 1)
            self.assertIn("Native GPU preflights", (root / "results.md").read_text())


if __name__ == "__main__":
    unittest.main()
