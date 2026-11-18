import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lost_tokens.core import atomic_json


loader = importlib.util.spec_from_file_location(
    "run_consensus", Path(__file__).resolve().parents[1] / "scripts/run_consensus.py"
)
study = importlib.util.module_from_spec(loader)
loader.loader.exec_module(study)


class ConsensusStudyTests(unittest.TestCase):
    def test_mmlu_is_voted_as_choices_from_the_declared_case_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "votes").mkdir()
            run = root / "member"
            atomic_json(
                run / "workers/one/outcomes/mmlu/one.json",
                {"id": "one", "task": "mmlu", "arm": "ours", "prediction": "C", "correct": True},
            )
            job = {
                "task": "mmlu",
                "repeat": 0,
                "member_index": 0,
                "arm": "ours",
                "run": str(run),
                "body_tokens": 10,
                "phase_wall_seconds": 1,
                "outcomes_sha256": "test",
            }
            manifest = {
                "cohort": {
                    "mmlu": {
                        "ids": ["one"],
                        "answer_schema": {
                            "one": {"answer_format": "choice", "choices": list("ABCD")}
                        },
                    }
                },
                "comparison": {
                    "mmlu": {
                        "baseline": {"one": {"correct": False}},
                        "previous_ours": {"one": {"correct": False}},
                    }
                },
            }
            with patch.object(study, "answer_consensus", wraps=study.answer_consensus) as voter:
                result = study.finish_vote(root, manifest, [job], "test")
            self.assertEqual(voter.call_args.kwargs["answer_format"], "choice")
            self.assertEqual(result["correct"], 1)

    def test_members_and_repeats_have_distinct_stable_seeds(self):
        cfg = study.load_pipeline(study.ROOT / "configs/consensus5.json")
        seeds = [
            study.member_seed(cfg, repeat, member["name"])
            for repeat in range(cfg["validation_repeats"])
            for member in cfg["members"]
        ]
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(study.member_seed(cfg, 0, "ar"), seeds[0])

    def test_voting_does_not_pick_correct_minority_or_use_completion_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "votes").mkdir()
            jobs = []
            # Correctness is visible only AFTER the majority prediction is selected.
            for index, prediction in enumerate(("B", "B", "B", "C", "C")):
                run = root / f"member-{index}"
                atomic_json(
                    run / "workers/worker0/outcomes/gpqa/one.json",
                    {
                        "id": "one",
                        "task": "gpqa",
                        "arm": "ours",
                        "prediction": prediction,
                        "correct": prediction == "C",
                        "gold": "C",
                    },
                )
                jobs.append(
                    {
                        "task": "gpqa",
                        "repeat": 0,
                        "member_index": index,
                        "arm": "ours",
                        "run": str(run),
                        "body_tokens": 10,
                        "phase_wall_seconds": 1,
                        "outcomes_sha256": str(index),
                    }
                )
            manifest = {
                "cohort": {
                    "gpqa": {
                        "ids": ["one"],
                        "answer_schema": {
                            "one": {"answer_format": "choice", "choices": ["A", "B", "C", "D"]}
                        },
                    }
                },
                "comparison": {
                    "gpqa": {
                        "baseline": {"one": {"correct": True}},
                        "previous_ours": {"one": {"correct": True}},
                    }
                },
            }
            result = study.finish_vote(root, manifest, list(reversed(jobs)), "test")
            case = json.loads((root / "votes/test.json").read_text())["cases"][0]
            self.assertEqual(case["vote"]["prediction"], "B")
            self.assertFalse(case["correct"])
            self.assertEqual(case["member_predictions"], ["B", "B", "B", "C", "C"])
            self.assertFalse(result["beats_both"])


if __name__ == "__main__":
    unittest.main()
