import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from results import validate, build, REQUIRED, digest


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

    def full_baseline(self):
        ids = [f"aime25-{i}" for i in range(30)]
        manifest = {"version": "full-v1", "datasets": {"aime25": {
            "n": 30, "full_n": 30, "ids": ids, "ids_sha256": digest(ids)
        }}}
        path = self.folder / "cohort-manifest.json"
        path.write_text(json.dumps(manifest))
        self.item.update(scope="full", cohort_version="full-v1",
                         cohort_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         code_branch="tester-code-2026-11-15")
        self.item["rows"][0].update(method="plain_ar", baseline={"n": 30, "correct": 18}, ours=None)
        self.write()
        return manifest, path

    def test_full_baseline_has_truthful_branch_and_completion_status(self):
        self.full_baseline()
        validate(self.folder, self.root)
        md, table = build(self.root)
        self.assertIn("baseline 완료 · ours 미측정", md)
        self.assertNotIn("ablation·AR 미측정", md)
        self.assertIn("60.00% (18/30)", md)
        self.assertIn("full-v1", table)

    def test_full_cohort_rejects_wrong_hash_coverage_duplicate_and_count(self):
        manifest, path = self.full_baseline()
        original = copy.deepcopy(manifest)
        path.write_text(path.read_text() + " ")
        with self.assertRaises(ValueError):
            validate(self.folder, self.root)
        for field, value in (("n", 29), ("full_n", 31), ("ids", ["duplicate"] * 30), ("ids_sha256", "f" * 64)):
            bad = copy.deepcopy(original)
            bad["datasets"]["aime25"][field] = value
            path.write_text(json.dumps(bad))
            self.item["cohort_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.write()
            with self.assertRaises(ValueError):
                validate(self.folder, self.root)
        path.write_text(json.dumps(original))
        self.item["cohort_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.item["rows"][0]["n_required"] = 31
        self.write()
        with self.assertRaises(ValueError):
            validate(self.folder, self.root)

    def shared_profile(self):
        manifest = {"version": "test-v1", "datasets": {"aime25": {"n": 30}}}
        path = self.root / "evaluation/subsets/test-v1/manifest.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(manifest))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        profile = {
            "cohort_version": "test-v1",
            "cohort_manifest_sha256": sha,
            "gpu_count": 4,
            "gpu_name_contains": "Test GPU",
            "batch_size_per_gpu": 8,
            "batch_size_by_task": {"aime25": 4},
        }
        (self.root / "evaluation/profiles.json").write_text(
            json.dumps({"profiles": {"test-hardware": profile}})
        )
        self.item.update(
            scope="shared",
            cohort_version="test-v1",
            cohort_manifest_sha256=sha,
            hardware_profile="test-hardware",
        )
        self.item["rows"][0].update(gpu_count=4, gpu_model="NVIDIA Test GPU", batch_size_per_gpu=4)
        self.write()

    def test_registered_profile_accepts_new_cohort(self):
        self.shared_profile()
        validate(self.folder, self.root)
        md, table = build(self.root)
        self.assertIn("## test-v1", md)
        self.assertIn("test-hardware", table)

    def test_profile_rejects_wrong_hardware_batch_manifest_and_missing_profile(self):
        self.shared_profile()
        original = copy.deepcopy(self.item)
        for field, value in (
            ("gpu_count", 8),
            ("gpu_model", "other GPU"),
            ("gpu_model", "NVIDIA Test GPU;other GPU"),
            ("batch_size_per_gpu", 8),
            ("n_required", 29),
        ):
            self.item = copy.deepcopy(original)
            self.item["rows"][0][field] = value
            self.write()
            with self.assertRaises(ValueError):
                validate(self.folder, self.root)

        for field, value in (
            ("hardware_profile", None),
            ("hardware_profile", "unknown"),
            ("cohort_manifest_sha256", "f" * 64),
            ("cohort_version", "../test-v1"),
        ):
            self.item = copy.deepcopy(original)
            self.item[field] = value
            self.write()
            with self.assertRaises(ValueError):
                validate(self.folder, self.root)

    def test_fixed_baseline_scores_must_match_the_referenced_outcomes(self):
        self.shared_profile()
        decoding = {
            "seed": 1,
            "max_output_tokens": 32768,
            "temperature": 0.6,
            "top_k": 20,
            "top_p": 0.95,
            "repetition_guard": {"enabled": True},
        }
        sources = {"lost_tokens/core.py": "a" * 64, "lost_tokens/math_scoring.py": "b" * 64}
        payload = {
            "conditions": {
                "cohort_manifest_sha256": self.item["cohort_manifest_sha256"],
                "hardware_profile": "test-hardware",
                "data": {"prompt_limit": 32768},
                "model": {
                    "name": "test",
                    "revision": "c" * 40,
                    "backend": "vllm",
                    "dtype": "bfloat16",
                },
                "decoding": decoding,
                "scoring_and_seed_sources": sources,
            },
            "outcomes": {"aime25": [{"id": str(i), "correct": i < 18} for i in range(30)]},
        }
        self.item["scorer_sha256"] = digest(sources)
        settings = {"prompt_limit": 32768, **{k: v for k, v in decoding.items() if k != "seed"}}
        self.item["evaluation_settings_sha256"] = digest(settings)
        self.item["baseline_reference_sha256"] = digest(payload)
        self.item["rows"][0]["baseline"] = {"n": 30, "correct": 18}
        ref = self.folder / "baseline-reference.json"
        ref.write_text(json.dumps({"payload": payload, "sha256": digest(payload)}))
        self.write()
        validate(self.folder, self.root)
        self.item["rows"][0]["baseline"]["correct"] = 19
        self.write()
        with self.assertRaises(ValueError):
            validate(self.folder, self.root)


if __name__ == "__main__":
    unittest.main()
