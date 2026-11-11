import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

from lost_tokens.cli import main
from lost_tokens.core import file_digest
from lost_tokens.data import normalize, raw_rows
from lost_tokens.math_scoring import math_correct, natural_answer
from test_portable import CharacterTokenizer


class MathDatasetTests(unittest.TestCase):
    def fixture(self, folder, task, records):
        name = "main/test-00000-of-00001.parquet" if task == "gsm8k" else "test.jsonl"
        path = Path(folder) / "inputs" / task / "fixed" / name
        path.parent.mkdir(parents=True)
        if task == "gsm8k":
            pq.write_table(pa.Table.from_pylist(records), path)
        else:
            path.write_text("".join(json.dumps(r) + "\n" for r in records))
        return {task: {"revision": "fixed", "files": {name: file_digest(path)}}}

    def rows(self, folder, task, records):
        with patch("lost_tokens.data.sources", return_value=self.fixture(folder, task, records)):
            rows = list(raw_rows(folder, task, 1))
            self.assertEqual(rows, list(raw_rows(folder, task, 999)))
            return rows

    def test_gsm8k_test_ids_and_final_numeric_answer_without_solution(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.rows(
                folder,
                "gsm8k",
                [
                    {"question": "How many?", "answer": "SECRET_SOLUTION\n#### 1,234"},
                    {"question": "What temperature?", "answer": "work\n#### -2.5"},
                ],
            )
        self.assertEqual([r["id"] for r in rows], ["gsm8k-test-0", "gsm8k-test-1"])
        self.assertEqual([r["gold"] for r in rows], ["1234", "-2.5"])
        for row in rows:
            self.assertEqual(row["answer_format"], "math")
            self.assertEqual(row["split"], "test")
            self.assertEqual(row["choices"], [])
            self.assertNotIn("answer", row)
            self.assertNotIn("SECRET_SOLUTION", json.dumps(row))
            self.assertEqual(
                normalize(row, CharacterTokenizer(), 1024)["question"], row["question"]
            )
            prediction = natural_answer("work \\boxed{" + row["gold"] + "}", row)
            self.assertTrue(math_correct(row["gold"], prediction))

    def test_gsm8k_rejects_missing_or_malformed_final_answer(self):
        for answer in ("42", "####", "#### 42 dollars", "#### 1,23", "#### NaN"):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as folder:
                with self.assertRaisesRegex(ValueError, "numeric final answer"):
                    self.rows(folder, "gsm8k", [{"question": "Q", "answer": answer}])

    def test_math500_preserves_latex_id_and_metadata_without_solution(self):
        with tempfile.TemporaryDirectory() as folder:
            row = self.rows(
                folder,
                "math500",
                [
                    {
                        "unique_id": "test/algebra/12.json",
                        "problem": "Compute one half.",
                        "answer": r"\frac{1}{2}",
                        "solution": "SECRET_SOLUTION",
                        "subject": "Algebra",
                        "level": 3,
                    }
                ],
            )[0]
        self.assertEqual(row["id"], "math500-test-algebra-12.json")
        self.assertEqual(Path(row["id"]).name, row["id"])
        self.assertEqual(row["source_id"], "test/algebra/12.json")
        self.assertEqual(row["gold"], r"\frac{1}{2}")
        self.assertEqual(row["question"], "Compute one half.")
        self.assertEqual((row["subject"], row["level"], row["split"]), ("Algebra", 3, "test"))
        self.assertNotIn("SECRET_SOLUTION", json.dumps(row))
        self.assertTrue(math_correct(row["gold"], natural_answer(r"\boxed{0.5}", row)))
        self.assertFalse(math_correct(row["gold"], natural_answer("0.5", row)))

    def test_math500_rejects_empty_identity_problem_or_answer(self):
        for field in ("unique_id", "problem", "answer"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                record = {
                    "unique_id": "id",
                    "problem": "Q",
                    "answer": "2",
                    "subject": "A",
                    "level": 1,
                }
                record[field] = " "
                with self.assertRaisesRegex(ValueError, "stable ID"):
                    self.rows(folder, "math500", [record])

    def test_corrupt_inputs_rejected_for_both_datasets(self):
        for task in ("gsm8k", "math500"):
            with self.subTest(task=task), tempfile.TemporaryDirectory() as folder:
                manifest = self.fixture(folder, task, [{"question": "Q", "answer": "#### 2"}])
                manifest[task]["files"] = dict.fromkeys(manifest[task]["files"], "0" * 64)
                with patch("lost_tokens.data.sources", return_value=manifest):
                    with self.assertRaisesRegex(ValueError, "Missing or corrupt"):
                        list(raw_rows(folder, task, 1))

    def test_cli_accepts_both_benchmarks(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch("lost_tokens.cli.download_datasets") as download,
        ):
            main(
                [
                    "download",
                    "--data-only",
                    "--benchmarks",
                    "gsm8k",
                    "math500",
                    "--work-dir",
                    folder,
                ]
            )
            download.assert_called_once_with(Path(folder).resolve(), ["gsm8k", "math500"])
