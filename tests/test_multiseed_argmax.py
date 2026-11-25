"""Matched-seed statistics, retrospective exclusion and immutable AR reuse."""

import copy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import digest, atomic_json

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location(
    "multiseed_controller", ROOT / "scripts/run_multiseed_argmax.py"
)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class MultiSeedTests(unittest.TestCase):
    def test_retirement_targets_only_matching_stopped_scheduler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "old"
            parent.mkdir()
            proc = root / "proc"
            proc.mkdir()

            def process(pid, study_path, state):
                p = proc / str(pid)
                p.mkdir()
                command = [
                    "/venv/bin/python",
                    "/code/scripts/run_multiseed_argmax.py",
                    "run",
                    "--study",
                    str(study_path),
                ]
                (p / "cmdline").write_bytes(b"\0".join(x.encode() for x in command) + b"\0")
                (p / "status").write_text("State:\t" + state + "\n")

            process(123, parent, "T (stopped)")
            process(124, root / "unrelated", "S (sleeping)")
            with patch.object(study.os, "kill") as kill:
                study.retire_stopped_parent(parent, root / "new", proc)
                kill.assert_called_once_with(123, study.signal.SIGKILL)
            self.assertEqual(
                study.read(parent / "superseded.json")["replacement_study"], str(root / "new")
            )
            (proc / "123" / "status").write_text("State:\tS (sleeping)\n")
            with patch.object(study.os, "kill") as kill:
                with self.assertRaisesRegex(RuntimeError, "still active"):
                    study.retire_stopped_parent(parent, root / "new", proc)
                kill.assert_not_called()

    def test_busy_supervisor_lock_is_observed_without_interrupting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "supervisor.lock").open("a") as lock:
                study.fcntl.flock(lock, study.fcntl.LOCK_EX | study.fcntl.LOCK_NB)
                self.assertTrue(study.supervisor_busy(root))
            self.assertFalse(study.supervisor_busy(root))

    def continuation_fixture(self, root):
        cfg = load_spec(ROOT / "configs/vllm-argmax.json")
        pipeline = study.read(ROOT / "configs/multiseed-argmax.json")
        old_pipeline = copy.deepcopy(pipeline)
        old_pipeline["seeds"] = [95025 if s == 42 else s for s in pipeline["seeds"]]
        m = {
            "source": {},
            "config": cfg,
            "cohort": {},
            "gpus": "0",
            "work_dir": str(root),
            "model_cache": str(root / "models"),
            "environment": {"runtime": {}},
            "pipeline": pipeline,
            "inputs": {},
        }
        parent = root / "parent"
        parent.mkdir()
        old = {**m, "pipeline": old_pipeline}
        atomic_json(parent / "manifest.json", old)
        atomic_json(parent / "manifest-sha256.json", {"sha256": digest(old)})
        seed_cfg = copy.deepcopy(cfg)
        seed_cfg["experiment"]["seed"] = 95022
        old_cfg = parent / "seed.json"
        new_cfg = root / "seed.json"
        atomic_json(old_cfg, seed_cfg)
        atomic_json(new_cfg, seed_cfg)
        baseline = parent / "baseline"
        ongoing = parent / "ours"
        for path in (baseline, ongoing):
            path.mkdir()
            atomic_json(path / "plan.json", {})
        outcomes = parent / "outcomes.json"
        atomic_json(outcomes, [{"id": "one", "correct": True}])
        ref = parent / "reference.json"
        sha = study.seal_reference(
            ref,
            {
                "seed": 95022,
                "task": "aime25",
                "n": 1,
                "correct": 1,
                "outcomes": [{"id": "one", "correct": True}],
            },
        )
        jobs = []
        for arm, path, status in [("baseline", baseline, "complete"), ("ours", ongoing, "running")]:
            job = {
                "seed": 95022,
                "task": "aime25",
                "arm": arm,
                "state": status,
                "run_path": str(path),
                "config_file": str(old_cfg),
                "reused": False,
                "n": 1 if arm == "baseline" else 0,
                "correct": 1 if arm == "baseline" else 0,
                "audits_passed": arm == "baseline",
                "started_at": "original-start",
                "deadline_epoch": None,
            }
            if arm == "baseline":
                job.update(
                    reference_file=str(ref), reference_sha256=sha, outcomes_file=str(outcomes)
                )
            jobs.append(job)
        jobs.append(
            {
                "seed": 95025,
                "task": "aime25",
                "arm": "baseline",
                "state": "queued",
                "n": 0,
                "run_path": str(parent / "unused"),
            }
        )
        atomic_json(parent / "status.json", {"started_at": "original-study-start", "jobs": jobs})
        new_jobs = [
            {
                "seed": 95022,
                "task": "aime25",
                "arm": arm,
                "reused": False,
                "state": "queued",
                "config_file": str(new_cfg),
                "estimated_seconds": 10,
            }
            for arm in ["baseline", "ours"]
        ]
        return SimpleNamespace(continuation_study=parent), m, new_jobs

    def test_seed_amendment_preserves_original_runs_references_and_deadlines(self):
        with tempfile.TemporaryDirectory() as directory:
            args, m, jobs = self.continuation_fixture(Path(directory))
            frozen = (args.continuation_study / "manifest.json").read_bytes()
            with patch.object(study, "validate_job_run"):
                start = study.continue_study(args, m, jobs)
            self.assertEqual(start, "original-study-start")
            self.assertEqual(jobs[0]["state"], "complete")
            self.assertEqual(jobs[1]["state"], "queued")
            self.assertEqual(jobs[1]["started_at"], "original-start")
            self.assertIsNone(jobs[1]["deadline_epoch"])
            self.assertEqual(Path(jobs[1]["run_path"]), args.continuation_study / "ours")
            self.assertEqual(m["seed_amendment"]["added_seeds"], [42])
            self.assertEqual(m["seed_amendment"]["removed_unstarted_seeds"], [95025])
            self.assertEqual((args.continuation_study / "manifest.json").read_bytes(), frozen)
            self.assertIn(jobs[0]["reference_file"], m["inputs"])

    def test_seed_amendment_rejects_dropping_started_seed_or_changed_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            args, m, jobs = self.continuation_fixture(Path(directory))
            (args.continuation_study / "unused").mkdir()
            with self.assertRaisesRegex(ValueError, "already started"):
                study.continue_study(args, m, jobs)

            (args.continuation_study / "unused").rmdir()
            m["source"] = {"altered": "source"}
            with self.assertRaisesRegex(ValueError, "inference"):
                study.continue_study(args, m, jobs)

    def reduction_fixture(self, root):
        args, m, jobs = self.continuation_fixture(root)
        parent = study.read(args.continuation_study / "manifest.json")
        parent["pipeline"]["seeds"] = m["pipeline"]["seeds"] + [95023]
        atomic_json(args.continuation_study / "manifest.json", parent)
        atomic_json(args.continuation_study / "manifest-sha256.json", {"sha256": digest(parent)})
        args.reduce_seeds = True
        state = study.read(args.continuation_study / "status.json")
        outcomes = root / "archived.json"
        records = [{"id": "one", "correct": True}]
        atomic_json(outcomes, records)
        state["jobs"].append(
            {
                "seed": 95023,
                "task": "aime25",
                "arm": "ours",
                "state": "complete",
                "audits_passed": True,
                "n": 1,
                "correct": 1,
                "outcomes_file": str(outcomes),
                "outcomes_sha256": digest(records),
            }
        )
        atomic_json(args.continuation_study / "status.json", state)
        return args, m, jobs, outcomes

    def test_scope_reduction_archives_completed_excluded_results_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            args, m, jobs, outcomes = self.reduction_fixture(Path(directory))
            before = outcomes.read_bytes()
            frozen = (args.continuation_study / "manifest.json").read_bytes()
            with patch.object(study, "validate_job_run"):
                study.continue_study(args, m, jobs)
            self.assertTrue(m["seed_amendment"]["scope_reduction"])
            self.assertEqual(m["seed_amendment"]["excluded_seeds"], [95023])
            self.assertEqual(len(m["seed_amendment"]["archived_completed_results"]), 1)
            self.assertEqual(outcomes.read_bytes(), before)
            self.assertEqual((args.continuation_study / "manifest.json").read_bytes(), frozen)
            self.assertIn(str(outcomes), m["inputs"])

    def test_scope_reduction_rejects_unfinished_excluded_work_and_changed_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            args, m, jobs, outcomes = self.reduction_fixture(Path(directory))
            atomic_json(outcomes, [{"id": "one", "correct": False}])
            with self.assertRaisesRegex(ValueError, "identity"):
                study.continue_study(args, m, jobs)
            atomic_json(outcomes, [{"id": "one", "correct": True}])
            state = study.read(args.continuation_study / "status.json")
            state["jobs"][-1].update(state="running", run_path=str(Path(directory) / "running"))
            atomic_json(args.continuation_study / "status.json", state)
            with self.assertRaisesRegex(ValueError, "already started"):
                study.continue_study(args, m, jobs)

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
