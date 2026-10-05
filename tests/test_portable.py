import copy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.core import atomic_json, digest, file_digest
from lost_tokens.data import choice_row, download_file, normalize, sources
from lost_tokens.reporting import report
from lost_tokens.cli import main as cli_main
from lost_tokens.protocol import planned_rows
from lost_tokens.runner import CheckpointStore, DeadlineReached, create_run


class CharacterTokenizer:
    def encode(self, text, **kwargs):
        return [ord(c) for c in text]

    def decode(self, ids, **kwargs):
        return "".join(chr(c) for c in ids)

    def apply_chat_template(self, messages, **kwargs):
        return self.encode(messages[0]["content"]) + [1]


class PortableTests(unittest.TestCase):
    def test_heartbeat_is_a_context_manager_and_stops_its_thread(self):
        from lost_tokens.runtime import heartbeat

        messages = []
        with heartbeat("loading", messages.append):
            self.assertEqual(messages, ["loading"])
        self.assertEqual(messages, ["loading"])

    def test_download_publishes_verified_partial_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "raw.json"
            partial = target.with_name(target.name + ".part")
            partial.write_bytes(b'{"verified":true}')
            sha = file_digest(partial)
            download_file("https://example.invalid/never-requested", target, sha, lambda _: None)
            self.assertEqual(file_digest(target), sha)
            self.assertFalse(partial.exists())
            download_file("https://example.invalid/never-requested", target, sha, lambda _: None)
            target.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                download_file("https://example.invalid", target, sha, lambda _: None)

    def test_manifest_has_all_pinned_sources_without_local_directories(self):
        self.assertEqual(set(sources()), {"aime25", "hmmt25", "gpqa", "longbench_v2", "supergpqa"})
        for entry in sources().values():
            self.assertEqual(len(entry["revision"]), 40)
            self.assertNotIn("directory", entry)
            self.assertTrue(entry["url_prefix"].startswith("https://"))
            self.assertTrue(all(len(x) == 64 for x in entry["files"].values()))

    def test_long_context_cut_preserves_question_and_options(self):
        row = choice_row(
            "longbench_v2",
            "one",
            "Which choice is correct?",
            ["First", "Second", "Third", "Fourth"],
            2,
            context="HEAD" + 2000 * "x" + "TAIL",
        )
        result = normalize(row, CharacterTokenizer(), 512)
        self.assertLessEqual(result["prompt_tokens"], 512)
        self.assertTrue(result["context_truncated"])
        self.assertIn("HEAD", result["question"])
        self.assertIn("TAIL", result["question"])
        self.assertIn(row["question"], result["question"])
        self.assertNotIn("context", result)
        self.assertEqual(result["gold"], "C")
        self.assertNotIn("Final answer: (C)", result["question"])

    def test_noncontext_questions_are_never_silently_truncated(self):
        row = choice_row("supergpqa", "one", "x" * 1000, ["one", "two"], 0)
        with self.assertRaises(ValueError):
            normalize(row, CharacterTokenizer(), 256)

    def test_deadline_blocks_work_and_valid_resume_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run"
            store = CheckpointStore(path, {"fixed": 1})
            self.assertEqual(store.call("first", {}, lambda: 7), 7)
            saved = next((path / "checkpoints").glob("*.json"))
            sha = file_digest(saved)
            store.deadline = time.monotonic() - 1
            with self.assertRaises(DeadlineReached):
                store.call("next", {}, lambda: self.fail("Executed expired work"))
            resumed = CheckpointStore(path, {"fixed": 1}, resume=True)
            self.assertEqual(resumed.call("first", {}, lambda: self.fail("Resampled")), 7)
            self.assertEqual(file_digest(saved), sha)
            with self.assertRaises(ValueError):
                CheckpointStore(path, {"fixed": 2}, resume=True)

    def test_run_creation_from_other_directory_has_paired_disjoint_rows(self):
        rows = [
            {
                "id": f"aime25-{i}",
                "task": "aime25",
                "question": "Q",
                "gold": "1",
                "choices": [],
                "answer_format": "math",
                "prompt_tokens": 8,
            }
            for i in range(5)
        ]
        with tempfile.TemporaryDirectory() as folder:
            spec = runtime_spec(load_spec(), folder)
            before = copy.deepcopy(spec)
            cwd = Path.cwd()
            try:
                os.chdir(folder)
                with (
                    patch("lost_tokens.runner.devices", return_value=["0", "1"]),
                    patch("lost_tokens.runner.load_prepared", return_value=rows),
                ):
                    run = create_run(
                        "another folder", spec, ["aime25"], gpus="0,1", limit=3, run_name="paired"
                    )
                self.assertEqual(spec, before)
                plan = json.loads((run / "plan.json").read_text())
                self.assertEqual(plan["counts"], {"aime25": 3})
                by_arm = {a: [] for a in plan["arms"]}
                for w in plan["workers"]:
                    split = json.loads((run / w["split"]).read_text())
                    by_arm[w["arm"]].append(
                        [r["id"] for r in split["tasks"]["aime25"]["evaluation"]]
                    )
                self.assertEqual(by_arm["baseline"], by_arm["ours"])
                self.assertFalse(set(by_arm["ours"][0]) & set(by_arm["ours"][1]))
                self.assertEqual(sum(map(len, by_arm["ours"])), 3)
            finally:
                os.chdir(cwd)

    def _subset_rows(self):
        return [
            {
                "id": f"aime25-{i}",
                "task": "aime25",
                "question": "Q",
                "gold": "1",
                "choices": [],
                "answer_format": "math",
                "prompt_tokens": 8,
            }
            for i in range(6)
        ]

    def _evaluation_rows(self, run):
        plan = json.loads((run / "plan.json").read_text())
        w = next(w for w in plan["workers"] if w["arm"] == "baseline")
        split = json.loads((run / w["split"]).read_text())
        cfg = json.loads((run / w["config"]).read_text())
        return plan, cfg, planned_rows(cfg, split, "study")

    def test_ids_subset_selection_and_seed_inputs_match_full_run(self):
        from lost_tokens.core import derived_seed

        rows = self._subset_rows()
        with tempfile.TemporaryDirectory() as folder:
            spec = runtime_spec(load_spec(), folder)
            ids_file = Path(folder) / "ids.json"
            ids_file.write_text(json.dumps({"ids": ["aime25-4", "aime25-1"]}))
            with (
                patch("lost_tokens.runner.devices", return_value=["0"]),
                patch("lost_tokens.runner.load_prepared", return_value=rows),
            ):
                full = create_run(folder, spec, ["aime25"], run_name="full")
                sub = create_run(
                    folder,
                    spec,
                    ["aime25"],
                    run_name="sub",
                    ids=["aime25-4", "aime25-1"],
                    ids_file=ids_file,
                )
                for bad in (["aime25-1", "nope"], ["aime25-1", "aime25-1"]):
                    with self.assertRaises(ValueError):
                        create_run(folder, spec, ["aime25"], run_name="bad", ids=bad)
                with self.assertRaises(ValueError):
                    create_run(folder, spec, ["aime25"], run_name="bad", ids=["aime25-1"], limit=2)
            _, full_cfg, full_rows = self._evaluation_rows(full)
            plan, sub_cfg, sub_rows = self._evaluation_rows(sub)
            self.assertEqual([r["id"] for _, r in sub_rows], ["aime25-1", "aime25-4"])
            self.assertEqual(plan["ids"], ["aime25-4", "aime25-1"])
            self.assertEqual(plan["ids_file"]["sha256"], file_digest(ids_file))
            self.assertEqual(plan["counts"], {"aime25": 2})
            lookup = {r["id"]: (ns, r) for ns, r in full_rows}
            for ns, row in sub_rows:
                self.assertEqual((ns, row), lookup[row["id"]])
                self.assertEqual(
                    derived_seed(sub_cfg["experiment"]["seed"], ns, row["id"]),
                    derived_seed(full_cfg["experiment"]["seed"], *lookup[row["id"]][:1], row["id"]),
                )

    def test_cli_rejects_ids_file_with_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            ids_file = Path(folder) / "ids.json"
            ids_file.write_text('["aime25-1"]')
            with self.assertRaises(SystemExit):
                cli_main(
                    ["run", "--work-dir", folder, "--limit", "2", "--ids-file", str(ids_file)]
                )

    def _make_run(self, folder, arms, rows=None, include_arms_key=True):
        run = Path(folder)
        plan = {"workers": [], "benchmarks": ["aime25"], "smoke": False}
        if include_arms_key:
            plan["arms"] = list(arms)
        for arm in arms:
            plan["workers"].append({"name": arm + "-worker0", "arm": arm})
            for ident, ok in (rows or {}).get(arm, {}).items():
                atomic_json(
                    run / "workers" / (arm + "-worker0") / "outcomes/aime25" / (ident + ".json"),
                    {
                        "task": "aime25",
                        "id": ident,
                        "finished_epoch": 1,
                        "correct": ok,
                        "body_tokens": 1,
                        "events": 0,
                        "thinking_complete": True,
                        "prediction": "1",
                    },
                )
        atomic_json(run / "plan.json", plan)
        return run

    def test_default_and_selected_arms_in_plan(self):
        rows = [
            {
                "id": f"aime25-{i}",
                "task": "aime25",
                "question": "Q",
                "gold": "1",
                "choices": [],
                "answer_format": "math",
                "prompt_tokens": 8,
            }
            for i in range(2)
        ]
        with tempfile.TemporaryDirectory() as folder:
            spec = runtime_spec(load_spec(), folder)
            with (
                patch("lost_tokens.runner.devices", return_value=["0"]),
                patch("lost_tokens.runner.load_prepared", return_value=rows),
            ):
                default = create_run(folder, spec, ["aime25"], run_name="d")
                only = create_run(folder, spec, ["aime25"], run_name="r", arms=["reference"])
                three = create_run(
                    folder, spec, ["aime25"], run_name="t", arms=["baseline", "reference", "ours"]
                )
                with self.assertRaises(ValueError):
                    create_run(folder, spec, ["aime25"], run_name="x", arms=["nope"])
            plan = json.loads((default / "plan.json").read_text())
            self.assertEqual(plan["arms"], ["baseline", "ours"])
            self.assertEqual(
                [(w["name"], w["condition"]) for w in plan["workers"]],
                [("baseline-worker0", "plain_ar"), ("ours-worker0", "filtered_futures")],
            )
            plan = json.loads((only / "plan.json").read_text())
            self.assertEqual(plan["arms"], ["reference"])
            self.assertEqual(
                [(w["name"], w["condition"]) for w in plan["workers"]],
                [("reference-worker0", "reference_only")],
            )
            cfg = json.loads((only / "configs/reference-worker0.json").read_text())
            self.assertEqual(cfg["experiment"]["arms"], ["reference_only"])
            plan = json.loads((three / "plan.json").read_text())
            self.assertEqual(len(plan["workers"]), 3)

    def test_cli_arms_choices(self):
        with self.assertRaises(SystemExit):
            cli_main(["run", "--arms", "bogus"])

    def test_old_plan_without_arms_key_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self._make_run(
                folder,
                ("baseline", "ours"),
                {"baseline": {"a": False}, "ours": {"a": True}},
                include_arms_key=False,
            )
            result = report(run)
            self.assertEqual(result["paired"]["all"]["difference_pp"], 100)
            self.assertNotIn("vs_baseline", result)

    def test_three_arm_report_has_both_pairings(self):
        data = {
            "baseline": {"a": True, "b": False, "c": False},
            "reference": {"a": False, "b": True, "c": True},
            "ours": {"a": True, "b": True, "c": False},
        }
        with tempfile.TemporaryDirectory() as folder:
            result = report(self._make_run(folder, list(data), data))
            pairs = result["vs_baseline"]
            self.assertEqual(
                (pairs["reference"]["all"]["wins"], pairs["reference"]["all"]["losses"]), (2, 1)
            )
            self.assertEqual(pairs["ours"]["all"]["wins"], 1)
            self.assertEqual(pairs["ours"]["all"]["n"], 3)
            self.assertEqual(result["paired"]["all"]["n"], 3)
            self.assertIn("reference", (Path(folder) / "report.md").read_text())

    def test_report_without_baseline(self):
        data = {"reference": {"a": True, "b": False}}
        with tempfile.TemporaryDirectory() as folder:
            result = report(self._make_run(folder, list(data), data))
            self.assertEqual(result["own"]["reference"]["all"]["correct"], 1)

    def test_report_without_baseline_uses_own_sets(self):
        data = {"reference": {"a": True, "b": False}, "ours": {"a": True, "b": True, "c": True}}
        with tempfile.TemporaryDirectory() as folder:
            result = report(self._make_run(folder, list(data), data))
            self.assertEqual(result["paired"]["all"]["n"], 2)
            text = (Path(folder) / "report.md").read_text()
            self.assertIn("| aime25 | 2 | 50.00% (1/2) | 100.00% (3/3) |", text)

    def _load_compare_runs(self):
        import importlib.util

        path = Path(__file__).resolve().parents[1] / "scripts" / "compare_runs.py"
        spec = importlib.util.spec_from_file_location("compare_runs", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_compare_runs_load_drops_late_outcomes(self):
        module = self._load_compare_runs()
        with tempfile.TemporaryDirectory() as folder:
            run = self._make_run(folder, ("ours",), {"ours": {"a": True, "b": True}})
            atomic_json(run / "workers/ours-worker0/outcomes/aime25/b.json", {
                "task": "aime25", "id": "b", "finished_epoch": 11, "correct": True,
            })
            atomic_json(run / "schedule.json", {"ours": {"deadline_epoch": 10}})
            self.assertEqual(sorted(module.load(run, "ours")), ["aime25/a"])

    def test_compare_runs_load_plan_workers_and_duplicates(self):
        module = self._load_compare_runs()
        with tempfile.TemporaryDirectory() as folder:
            run = self._make_run(folder, ("ours",), {"ours": {"a": True}})
            stray = {"task": "aime25", "id": "stray", "finished_epoch": 1, "correct": True}
            atomic_json(run / "workers/ours-worker9/outcomes/aime25/stray.json", stray)
            self.assertEqual(sorted(module.load(run, "ours")), ["aime25/a"])
            plan = json.loads((run / "plan.json").read_text())
            plan["workers"].append({"name": "ours-worker1", "arm": "ours"})
            atomic_json(run / "plan.json", plan)
            atomic_json(
                run / "workers/ours-worker1/outcomes/aime25/a.json",
                {"task": "aime25", "id": "a", "finished_epoch": 1, "correct": False},
            )
            with self.assertRaises(ValueError):
                module.load(run, "ours")

    def test_compare_runs_script(self):
        import contextlib
        import importlib.util
        import io

        path = Path(__file__).resolve().parents[1] / "scripts" / "compare_runs.py"
        spec = importlib.util.spec_from_file_location("compare_runs", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            a = self._make_run(
                Path(folder) / "a",
                ("baseline", "ours"),
                {"baseline": {"x": True, "y": False}, "ours": {"x": False, "y": True}},
            )
            b = self._make_run(
                Path(folder) / "b", ("reference",), {"reference": {"x": True, "y": True, "z": True}}
            )
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                module.main([str(a), str(b), "--baseline", f"{a}:baseline"])
            text = out.getvalue()
            self.assertIn("| a | ours | 2 |", text)
            self.assertIn("| b | reference | 2 | 50.00% (1) | 100.00% (2) | 1 | 0 | +50.00 |", text)
            self.assertIn("b [reference] wins: aime25/y", text)

    def test_reports_only_common_on_time_cases(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)
            workers = []
            for arm in ("baseline", "ours"):
                workers.append({"name": arm, "arm": arm})
                for ident, end in [("shared", 9), (arm, 9), ("late", 11)]:
                    atomic_json(
                        run / "workers" / arm / "outcomes/aime25" / (ident + ".json"),
                        {
                            "task": "aime25",
                            "id": ident,
                            "finished_epoch": end,
                            "correct": arm == "ours",
                            "body_tokens": 10,
                            "events": 0,
                            "thinking_complete": True,
                        },
                    )
            atomic_json(
                run / "plan.json",
                {
                    "arms": ["baseline", "ours"],
                    "workers": workers,
                    "benchmarks": ["aime25"],
                    "smoke": False,
                },
            )
            atomic_json(
                run / "schedule.json", {a: {"deadline_epoch": 10} for a in ("baseline", "ours")}
            )
            result = report(run)
            self.assertEqual(result["paired"]["all"]["n"], 1)
            self.assertEqual(result["paired"]["all"]["difference_pp"], 100)
            self.assertEqual(result["own"]["ours"]["all"]["n"], 2)


if __name__ == "__main__":
    unittest.main()
