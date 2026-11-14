"""Offline integrity checks for the two canonical hardware cohorts."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


class ProfileIntegrityTests(unittest.TestCase):
    def test_frozen_cohorts_and_parent_membership(self):
        registry = json.loads((ROOT / "evaluation/profiles.json").read_text())["profiles"]
        expected = {
            "l40s-4gpu": ("l40s-2h-v1", 4, [30, 25, 1319, 90, 125, 550]),
            "pro6000-8gpu": ("shared-v1", 8, [30, 30, 1319, 448, 250, 3511]),
        }
        tasks = ["aime25", "hmmt25", "gsm8k", "gpqa", "math500", "mmlu"]
        parent_path = ROOT / "evaluation/subsets/shared-v1/manifest.json"
        self.assertEqual(
            hashlib.sha256(parent_path.read_bytes()).hexdigest(),
            "978ce5fe9ad30bf6edd6636d7ce88fe39b3bd367e397989f10de29cec07171f3",
        )
        for name, (version, gpu_count, counts) in expected.items():
            profile = registry[name]
            self.assertEqual(profile["cohort_version"], version)
            self.assertEqual(profile["gpu_count"], gpu_count)
            path = ROOT / "evaluation/subsets" / version / "manifest.json"
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), profile["cohort_manifest_sha256"]
            )
            manifest = json.loads(path.read_text())
            self.assertFalse(manifest["selection_uses_answers"])
            for task, n in zip(tasks, counts):
                entry = manifest["datasets"][task]
                ids_path = path.parent / entry["ids_file"]
                ids = json.loads(ids_path.read_text())["ids"]
                self.assertEqual(entry["n"], n)
                self.assertEqual(len(ids), n)
                self.assertEqual(len(set(ids)), n)
                self.assertEqual(
                    hashlib.sha256(ids_path.read_bytes()).hexdigest(), entry["ids_file_sha256"]
                )
                self.assertEqual(digest(ids), entry["ids_sha256"])
                self.assertEqual(sum(entry["strata_counts"].values()), n)
                if version == "l40s-2h-v1":
                    parent_ids = json.loads((parent_path.parent / entry["ids_file"]).read_text())[
                        "ids"
                    ]
                    self.assertLessEqual(set(ids), set(parent_ids))
                    self.assertEqual(
                        profile["batch_size_by_task"].get(task, profile["batch_size_per_gpu"]),
                        entry["batch_size_per_gpu"],
                    )
            if version == "l40s-2h-v1":
                evidence = ROOT / "evaluation/measurements/l40s-2h-v1/forecast.json"
                self.assertEqual(
                    hashlib.sha256(evidence.read_bytes()).hexdigest(), manifest["forecast_sha256"]
                )


if __name__ == "__main__":
    unittest.main()
