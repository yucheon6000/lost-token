import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from lost_tokens.core import atomic_json
from lost_tokens.performance import (
    compare_performance,
    outcome_costs,
    performance_vs_baseline,
    phase_wall_seconds,
)
from lost_tokens.reporting import report


def row(seconds, body=100, forward=200, **extra):
    return {
        "task": "mmlu",
        "seconds": seconds,
        "body_tokens": body,
        "forward_tokens": forward,
        "correct": True,
        **extra,
    }


class PerformanceTests(unittest.TestCase):
    def test_parallel_phase_wall_time_is_separate_from_summed_case_time(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            schedule = {"ours": {"start_epoch": 1}}
            self.assertIsNone(phase_wall_seconds(run, "ours", schedule))
            atomic_json(run / "ours-complete.json", {"at": "1970-01-01T00:00:11+00:00"})
            self.assertEqual(phase_wall_seconds(run, "ours", schedule), 10)
            atomic_json(
                run / "ours-complete.json",
                {"at": "1970-01-01T00:00:11+00:00", "expired_before_resume": True},
            )
            self.assertIsNone(phase_wall_seconds(run, "ours", schedule))

    def test_compares_identical_completed_subset_and_reports_true_ratios(self):
        b = {"a": row(1), "b": row(3), "baseline_only": row(1000)}
        a = {"a": row(2, 80, 300), "b": row(4, 120, 500), "ours_only": row(0.01)}
        p = compare_performance(b, a)
        self.assertEqual((p["n"], p["timed_n"]), (2, 2))
        self.assertEqual(p["baseline"]["mean_case_seconds"], 2)
        self.assertEqual(p["arm"]["median_case_seconds"], 3)
        self.assertEqual(p["slowdown_percent"], 50)
        self.assertAlmostEqual(p["throughput_change_percent"], -100 / 3)
        self.assertEqual(p["costs"]["forward_tokens"]["change_percent"], 100)

    def test_resume_missing_nonfinite_and_zero_times_are_not_zero_cost_samples(self):
        b = {str(i): row(1) for i in range(5)}
        a = {
            "0": row(0),
            "1": row(None),
            "2": row(float("nan")),
            "3": row(0.01, timing_complete=False),
            "4": row(0.5, timing_complete=True),
        }
        p = compare_performance(b, a)
        self.assertEqual(p["n"], 5)
        self.assertEqual(p["timed_n"], 1)
        self.assertEqual(p["resumed_excluded_n"], 1)
        self.assertEqual(p["slowdown_percent"], -50)
        json.dumps(p, allow_nan=False)

    def test_missing_costs_and_empty_sets_are_pending(self):
        p = compare_performance({"a": row(1)}, {"a": {"seconds": 2}})
        self.assertIsNone(p["costs"]["forward_tokens"]["change_percent"])
        self.assertIsNone(p["arm"]["body_tokens_per_second"])
        self.assertIsNone(compare_performance({}, {})["time_ratio"])

    def test_pairwise_timing_does_not_require_third_arm_completion(self):
        p = performance_vs_baseline(
            {
                "baseline": {"a": row(1), "b": row(1)},
                "ours": {"a": row(2), "b": row(2)},
                "reference": {"a": row(3)},
            },
            ["mmlu"],
        )
        self.assertEqual(p["ours"]["mmlu"]["timed_n"], 2)
        self.assertEqual(p["reference"]["mmlu"]["timed_n"], 1)

    def test_outcomes_copy_durable_trace_costs_and_identify_partial_replay(self):
        result = {
            "policy_cost": {"seconds": 2, "forward_tokens": 42},
            "embedding_cost": {"seconds": 0.5},
            "recovery_seconds": 0.1,
            "events": [{"previews": [{"ids": [1, 2]}, {"ids": [3]}], "memory_ids": [4]}],
        }
        p = outcome_costs({"timing_checkpoint_hits": 2}, result)
        self.assertFalse(p["timing_complete"])
        self.assertEqual(p["candidate_tokens"], 3)
        self.assertEqual(p["memory_insertions"], 1)
        self.assertIsNone(outcome_costs({}, result)["timing_complete"])

    def test_json_and_markdown_reports_include_slowdown(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            atomic_json(
                run / "plan.json",
                {
                    "arms": ["baseline", "ours"],
                    "smoke": False,
                    "benchmarks": ["mmlu"],
                    "workers": [{"arm": a, "name": a} for a in ["baseline", "ours"]],
                },
            )
            for arm, seconds in [("baseline", 1), ("ours", 1.25)]:
                atomic_json(
                    run / f"workers/{arm}/outcomes/mmlu/a.json",
                    row(seconds, id="a", finished_epoch=1, events=0, thinking_complete=True),
                )
            p = report(run)
            self.assertEqual(p["performance_vs_baseline"]["ours"]["all"]["slowdown_percent"], 25)
            self.assertIn("+25.00%", (run / "report.md").read_text())
            self.assertEqual(p["own"]["ours"]["all"]["performance"]["mean_case_seconds"], 1.25)

    def test_offline_compare_saves_machine_readable_timing(self):
        path = Path(__file__).resolve().parents[1] / "scripts/compare_runs.py"
        spec = importlib.util.spec_from_file_location("compare_speed", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.compare({"a": row(2)}, {"a": row(3)})["performance"]["slowdown_percent"], 50
        )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs = []
            for arm, seconds in [("baseline", 2), ("ours", 3)]:
                run = root / arm
                atomic_json(run / "plan.json", {"workers": [{"name": "worker0", "arm": arm}]})
                path = run / "workers/worker0/outcomes/mmlu/a.json"
                atomic_json(path, row(seconds, id="a", finished_epoch=1, timing_complete=True))
                inputs.append((path, path.read_bytes()))
            with contextlib.redirect_stdout(io.StringIO()):
                module.main(
                    [
                        str(root / "baseline"),
                        str(root / "ours"),
                        "--baseline",
                        str(root / "baseline") + ":baseline",
                        "--output-dir",
                        str(root / "comparison"),
                    ]
                )
            saved = json.loads((root / "comparison/comparison.json").read_text())
            self.assertEqual(
                saved["comparisons"][0]["performance_by_task"]["mmlu"]["slowdown_percent"], 50
            )
            self.assertIn("+50.00%", (root / "comparison/comparison.md").read_text())
            self.assertIn("Arm correct", (root / "comparison/comparison.md").read_text())
            for path, original in inputs:
                self.assertEqual(path.read_bytes(), original)
