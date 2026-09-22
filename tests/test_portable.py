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
