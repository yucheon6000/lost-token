import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from results import validate, build, REQUIRED


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / "experiment-results/tester-2026-11-15"
        self.folder.mkdir(parents=True)
        self.item = {
            "id": self.folder.name,
            "code_branch": self.folder.name,
            "code_commit": "a" * 40,
            "cohort_version": "pilot",
            "cohort_manifest_sha256": "b" * 64,
            "scope": "historical-ablation",
            "model": "test",
            "model_revision": "c" * 40,
            "backend": "vllm",
            "dtype": "bfloat16",
            "seed": 1,
            "scorer_sha256": "d" * 64,
            "evaluation_settings_sha256": "e" * 64,
            "rows": [
                {
                    "dataset": "aime25",
                    "method": "argmax",
                    "n_required": 30,
                    "baseline": None,
                    "ours": {"correct": 18, "n": 30},
                    "gpu_count": 8,
                    "gpu_model": "GPU",
                    "audits_passed": True,
                }
            ],
        }
        for name in REQUIRED:
            (self.folder / name).write_text("content")
        self.write()

    def write(self):
        (self.folder / "submission.json").write_text(json.dumps(self.item))

    def test_missing_baseline_is_not_relabelled_from_ours(self):
        validate(self.folder, self.root)
        md, table = build(self.root)
        self.assertIn("미측정", md)
        self.assertIn("60.00% (18/30)", md)
        self.assertIn("ablation·AR 미측정", md)

    def test_invalid_count_or_missing_environment_rejected(self):
        self.item["rows"][0]["ours"]["correct"] = 31
        self.write()
        with self.assertRaises(ValueError):
            validate(self.folder, self.root)
        (self.folder / "environment.json").unlink()
        with self.assertRaises(ValueError):
            validate(self.folder, self.root)

    def test_comparison_groups_separate_backend_and_scorer(self):
        folder = self.root / "experiment-results/other-2026-11-15"
        folder.mkdir()
        other = copy.deepcopy(self.item)
        other.update(id=folder.name, code_branch=folder.name, backend="transformers")
        for name in REQUIRED:
            (folder / name).write_text("content")
        (folder / "submission.json").write_text(json.dumps(other))
        md, _ = build(self.root)
        self.assertEqual(md.count("## pilot"), 2)

    def test_render_is_deterministic(self):
        self.assertEqual(build(self.root), build(self.root))


if __name__ == "__main__":
    unittest.main()
