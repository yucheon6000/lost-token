import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from lost_tokens.cli import main
from lost_tokens.config import load_spec
from lost_tokens.core import file_digest
from lost_tokens.data import raw_rows
from lost_tokens.math_scoring import natural_answer
from lost_tokens.runner import create_run


class MMLUTests(unittest.TestCase):
    def fixture(self, folder, choices=None, answer=2):
        root = Path(folder) / "inputs/mmlu/fixed"
        root.mkdir(parents=True)
        path = root / "all/test-00000-of-00001.parquet"
        path.parent.mkdir()
        pq.write_table(
            pa.Table.from_pylist(
                [
                    {
                        "question": "Which value?",
                        "subject": subject,
                        "choices": choices or ["one", "two", "three", "four"],
                        "answer": answer,
                    }
                    for subject in ("abstract_algebra", "anatomy")
                ]
            ),
            path,
        )
        return {
            "mmlu": {
                "revision": "fixed",
                "files": {"all/test-00000-of-00001.parquet": file_digest(path)},
            }
        }

    def test_test_split_subject_ids_and_original_choice_order(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("lost_tokens.data.sources", return_value=self.fixture(folder)):
                rows = list(raw_rows(folder, "mmlu", 1))
                self.assertEqual(rows, list(raw_rows(folder, "mmlu", 999)))
            self.assertEqual([r["id"] for r in rows], ["mmlu-abstract_algebra-0", "mmlu-anatomy-1"])
            for row in rows:
                self.assertEqual(row["gold"], "C")
                self.assertEqual(row["choices"], list("ABCD"))
                self.assertEqual(row["split"], "test")
                self.assertIn("(A) one\n(B) two\n(C) three\n(D) four", row["question"])
                self.assertNotIn("Final answer", row["question"])
                self.assertIsNone(natural_answer("Reasoning about (C)", row))
                self.assertEqual(natural_answer("Final answer: (C)", row), row["gold"])

    def test_rejects_wrong_choice_count_and_invalid_answer(self):
        for choices, answer in [(["a", "b", "c"], 0), (None, 4), (None, -1)]:
            with (
                self.subTest(choices=choices, answer=answer),
                tempfile.TemporaryDirectory() as folder,
            ):
                with patch(
                    "lost_tokens.data.sources", return_value=self.fixture(folder, choices, answer)
                ):
                    with self.assertRaises(ValueError):
                        list(raw_rows(folder, "mmlu", 1))

    def test_refuses_corrupt_pinned_file(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = self.fixture(folder)
            manifest["mmlu"]["files"]["all/test-00000-of-00001.parquet"] = "0" * 64
            with patch("lost_tokens.data.sources", return_value=manifest):
                with self.assertRaisesRegex(ValueError, "Missing or corrupt"):
                    list(raw_rows(folder, "mmlu", 1))

    def test_cli_routes_mmlu_download(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch("lost_tokens.cli.download_datasets") as download,
        ):
            main(["download", "--data-only", "--benchmarks", "mmlu", "--work-dir", folder])
            download.assert_called_once_with(Path(folder).resolve(), ["mmlu"])

    def test_uneven_worker_shards_pair_exact_same_mmlu_questions(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("lost_tokens.data.sources", return_value=self.fixture(folder)):
                rows = list(raw_rows(folder, "mmlu", 1))
            with (
                patch("lost_tokens.runner.load_prepared", return_value=rows),
                patch("lost_tokens.runner.devices", return_value=["0", "1", "2"]),
            ):
                run = create_run(folder, load_spec(), ["mmlu"], gpus="0,1,2", run_name="test")
            plan = json.loads((run / "plan.json").read_text())
            self.assertEqual(plan["counts"], {"mmlu": 2})
            for i in range(3):
                self.assertEqual(
                    (run / f"configs/baseline-worker{i}-split.json").read_bytes(),
                    (run / f"configs/ours-worker{i}-split.json").read_bytes(),
                )
