"""Matched-seed statistics, retrospective exclusion and immutable AR reuse."""

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from lost_tokens.config import load_spec
from lost_tokens.core import digest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location(
    "multiseed_controller", ROOT / "scripts/run_multiseed_argmax.py"
)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class MultiSeedTests(unittest.TestCase):
    def test_pipeline_requires_all_six_tasks_and_distinct_matched_seeds(self):
        cfg = load_spec(ROOT / "configs/vllm-argmax.json")
        pipe = study.read(ROOT / "configs/multiseed-argmax.json")
        study.validate_pipeline(pipe, cfg)
        for update in (
            {"benchmarks": ["aime25", "hmmt25", "gpqa"]},
            {"seeds": [95021, 95022, 95022]},
            {"arms": ["ours"]},
            {"historical_seed": 95022},
            {"seeds": [True, 95021, 95022]},
        ):
            with self.assertRaises(ValueError):
                study.validate_pipeline({**pipe, **update}, cfg)
        bad = copy.deepcopy(cfg)
        bad["experiment"]["temperature"] = 0.7
        with self.assertRaises(ValueError):
            study.validate_pipeline(pipe, bad)

    def test_paired_counts_use_same_question_ids_and_no_answer_voting(self):
        b = {"one": {"correct": True}, "two": {"correct": False}, "three": {"correct": False}}
        o = {"one": {"correct": False}, "two": {"correct": True}, "three": {"correct": True}}
        result = study.paired_summary(b, o)
        self.assertEqual(result["gains"], 2)
        self.assertEqual(result["losses"], 1)
        self.assertAlmostEqual(result["delta_pp"], 100 / 3)
        with self.assertRaises(ValueError):
            study.paired_summary(b, {"other": {"correct": True}})

    def test_primary_mean_and_sample_sd_exclude_historical_and_partial_seeds(self):
        jobs = []
        cohort = {t: {"n": 100} for t in study.TASKS}
        for task in study.TASKS:
            for seed, delta in [(95021, 40), (95022, 1), (95023, 3)]:
                for arm in ("baseline", "ours"):
                    jobs.append(
                        {
                            "task": task,
                            "seed": seed,
                            "arm": arm,
                            "state": "complete",
                            "audits_passed": True,
                            "n": 100,
                            "correct": 50 + (delta if arm == "ours" else 0),
                            "gains": delta,
                            "losses": 0,
                        }
                    )
        m = {
            "cohort": cohort,
            "pipeline": {"seeds": [95021, 95022, 95023], "historical_seed": 95021},
        }
        groups = study.analyze({"jobs": jobs}, m)
        self.assertEqual(groups["gpqa"]["prospective"]["seeds"], 2)
        self.assertEqual(groups["gpqa"]["prospective"]["delta_pp"]["mean"], 2)
        self.assertAlmostEqual(groups["gpqa"]["prospective"]["delta_pp"]["sample_sd"], 2**0.5)
        self.assertNotEqual(groups["gpqa"]["all_seeds"]["delta_pp"]["mean"], 2)
        next(j for j in jobs if j["task"] == "gpqa" and j["seed"] == 95023 and j["arm"] == "ours")[
            "state"
        ] = "running"
        groups = study.analyze({"jobs": jobs}, m)
        self.assertEqual(groups["gpqa"]["prospective"]["seeds"], 1)
        self.assertEqual(groups["gpqa"]["prospective"]["delta_pp"]["mean"], 1)
        self.assertIsNone(groups["gpqa"]["prospective"]["delta_pp"]["sample_sd"])

    def test_frozen_reference_is_never_overwritten_and_seed_swap_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.json"
            payload = {
                "seed": 95022,
                "task": "gpqa",
                "n": 1,
                "correct": 1,
                "outcomes": [{"id": "one", "correct": True}],
                "deadline_epoch": None,
            }
            sha = study.seal_reference(path, payload)
            original = path.read_bytes()
            self.assertEqual(study.seal_reference(path, payload), sha)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                study.seal_reference(path, {**payload, "correct": 0})
            job = {
                "seed": 95022,
                "task": "gpqa",
                "arm": "baseline",
                "state": "complete",
                "audits_passed": True,
                "n": 1,
                "correct": 1,
                "reference_file": str(path),
                "reference_sha256": sha,
            }
            self.assertEqual(study.baseline_for({"jobs": [job]}, 95022, "gpqa")["sha256"], sha)
            other = Path(directory) / "other.json"
            swapped = {**payload, "seed": 95023}
            other_sha = study.seal_reference(other, swapped)
            with self.assertRaises(ValueError):
                study.baseline_for(
                    {
                        "jobs": [
                            {**job, "reference_file": str(other), "reference_sha256": other_sha}
                        ]
                    },
                    95022,
                    "gpqa",
                )
            with self.assertRaises(ValueError):
                study.baseline_for({"jobs": [{**job, "state": "running"}]}, 95022, "gpqa")


if __name__ == "__main__":
    unittest.main()
