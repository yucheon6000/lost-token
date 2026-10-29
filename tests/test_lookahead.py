"""Lookahead selection, memory preamble and the selected_only arm.

Reuses the tiny-model fixture of RecurrentTests and the audit harness of KnobTests.
"""

import json
import unittest
from unittest.mock import patch

from lost_tokens.core import RunStore, file_digest
from lost_tokens.recurrent_memory import (
    StreamDecoder,
    instruction,
    memory_text,
    run_condition,
    select_rollout,
)
from lost_tokens.protocol import PausableStore, RequestedPause
from lost_tokens.config import load_spec
from lost_tokens.runner import ARM_CONDITIONS
import test_recurrent_memory as base
import test_knobs as knobs


PREAMBLE = "Started but not followed; unverified."
LOOKAHEAD = {"statistic": "mean_logprob", "margin": 0.1, "min_tokens": 1}


def preview(rank, lps, text="x", stop_marker=None, ids=None, entropies=None):
    ids = ids if ids is not None else list(range(65, 65 + len(lps)))
    return {
        "rank": rank,
        "ids": ids,
        "text": text,
        "stop_marker": stop_marker,
        "raw_log_probabilities": lps,
        "entropies": entropies if entropies is not None else [0.5] * len(lps),
    }


class SelectRolloutTests(unittest.TestCase):
    EOS = {127}

    def exp(self, **lookahead):
        return {"selection": "lookahead", "lookahead": {**LOOKAHEAD, **lookahead}}

    def test_argmax_keeps_rank_one(self):
        result = select_rollout(
            [preview(1, [-0.1, -3.0]), preview(2, [-1.0, -0.1])], {"selection": "argmax"}, self.EOS
        )
        self.assertEqual(
            result, {"rule": "argmax", "selected_rank": 1, "flipped": False, "scores": []}
        )

    def test_flips_when_margin_exceeded_and_first_token_is_ignored(self):
        # Rank 1 has the better forced first token but the worse continuation.
        previews = [preview(1, [-0.1, -2.0, -2.0]), preview(2, [-1.5, -0.2, -0.2])]
        result = select_rollout(previews, self.exp(), self.EOS)
        self.assertTrue(result["flipped"])
        self.assertEqual(result["selected_rank"], 2)
        self.assertAlmostEqual(result["scores"][0]["value"], -2.0)
        self.assertAlmostEqual(result["scores"][1]["value"], -0.2)

    def test_no_flip_inside_margin(self):
        previews = [preview(1, [-0.1, -1.0]), preview(2, [-1.5, -0.95])]
        self.assertFalse(select_rollout(previews, self.exp(), self.EOS)["flipped"])
        self.assertTrue(select_rollout(previews, self.exp(margin=0.0), self.EOS)["flipped"])

    def test_best_alternative_wins_and_ties_prefer_lower_rank(self):
        previews = [preview(1, [-0.1, -2.0]), preview(2, [-1, -0.5]), preview(3, [-1, -0.2])]
        self.assertEqual(select_rollout(previews, self.exp(), self.EOS)["selected_rank"], 3)
        previews[2] = preview(3, [-1, -0.5])
        self.assertEqual(select_rollout(previews, self.exp(), self.EOS)["selected_rank"], 2)

    def test_terminal_short_or_blank_alternatives_are_ineligible(self):
        reference = preview(1, [-0.1, -2.0, -2.0])
        cases = [
            ("terminal", preview(2, [-1, -0.1, -0.1], stop_marker="</think>")),
            ("terminal", preview(2, [-1, -0.1, -0.1], ids=[66, 67, 127])),
            ("short", preview(2, [-1])),
            ("blank", preview(2, [-1, -0.1, -0.1], text="  ")),
        ]
        for reason, alternative in cases:
            result = select_rollout([reference, alternative], self.exp(), self.EOS)
            self.assertFalse(result["flipped"], reason)
            self.assertIn(reason, result["scores"][1]["reasons"])
        result = select_rollout(
            [reference, preview(2, [-1, -0.1])], self.exp(min_tokens=2), self.EOS
        )
        self.assertFalse(result["flipped"])

    def test_ineligible_reference_is_never_flipped_away_from(self):
        reference = preview(1, [-0.1, -2.0], stop_marker="</think>")
        result = select_rollout([reference, preview(2, [-1, -0.1])], self.exp(), self.EOS)
        self.assertFalse(result["flipped"])
        self.assertEqual(result["scores"][0]["reasons"], ["terminal"])
        result = select_rollout([preview(1, [-0.1])], self.exp(), self.EOS)
        self.assertEqual(result["selected_rank"], 1)
        self.assertIsNone(result["scores"][0]["value"])

    def test_entropy_statistic_uses_recorded_entropies(self):
        previews = [
            preview(1, [-0.1, -0.1, -0.1], entropies=[0.1, 2.0, 2.0]),
            preview(2, [-1.0, -1.0, -1.0], entropies=[3.0, 0.2, 0.2]),
        ]
        result = select_rollout(previews, self.exp(statistic="neg_mean_entropy"), self.EOS)
        self.assertEqual(result["selected_rank"], 2)
        self.assertAlmostEqual(result["scores"][1]["value"], -0.2)
        self.assertFalse(select_rollout(previews, self.exp(), self.EOS)["flipped"])


class LookaheadRunTests(unittest.TestCase):
    setUpClass = classmethod(base.RecurrentTests.setUpClass.__func__)
    setUp = base.RecurrentTests.setUp
    eligible = staticmethod(base.RecurrentTests.eligible)
    keep = staticmethod(base.RecurrentTests.keep)
    controlled = base.RecurrentTests.controlled
    audited = knobs.KnobTests.audited

    @staticmethod
    def biased_rollout(better_first_token=66):
        """Give one candidate (rank 2 by default) a clearly better continuation."""
        original = StreamDecoder.rollout

        def rollout(decoder, root, first, seed, count=None):
            out = original(decoder, root, first, seed, count)
            if first == better_first_token:
                out["raw_log_probabilities"] = [-0.05] * len(out["ids"])
                out["entropies"] = [0.01] * len(out["ids"])
            return out

        return patch.object(StreamDecoder, "rollout", rollout)

    def lookahead(self, **extra):
        self.cfg["experiment"].update(selection="lookahead", lookahead=dict(LOOKAHEAD), **extra)

    def test_rollouts_record_one_entropy_per_token(self):
        result = self.controlled(RunStore(self.root / "ent", {}))
        for event in result["events"]:
            for n in event["previews"]:
                self.assertEqual(len(n["entropies"]), len(n["ids"]))
                self.assertTrue(all(e >= 0 for e in n["entropies"]))
            self.assertEqual(event["selection"]["rule"], "argmax")

    def test_preamble_heads_every_memory_block_and_audits(self):
        self.cfg["experiment"]["memory_preamble"] = PREAMBLE
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            ],
        )
        self.assertEqual(reviewed["events"], 4)
        for event in result["events"]:
            self.assertTrue(
                event["memory_text"].startswith("\n<possibilities>\n" + PREAMBLE + "\n\n")
            )
            self.assertEqual(event["memory_text"].count(PREAMBLE), 1)
        self.assertEqual(memory_text([], None), "\n<possibilities>\n\n</possibilities>\n")
        self.assertIn("&lt;think&gt;x", memory_text([{"text": "a"}], "<think>x"))

    def test_lookahead_flips_commits_alternative_and_remembers_former_reference(self):
        self.lookahead()
        with self.biased_rollout():
            result = self.controlled(RunStore(self.root / "flip", {}), arm="all_futures")
        self.assertEqual(len(result["events"]), 4)
        # The last event's rollout is capped to one token by max_output_tokens, so it
        # has no continuation and stays with rank 1 (reason "short").
        last = result["events"][-1]
        self.assertEqual(last["selected_rank"], 1)
        self.assertEqual(last["selection"]["scores"][1]["reasons"], ["short"])
        for event in result["events"][:3]:
            self.assertEqual(event["selected_rank"], 2)
            self.assertTrue(event["selection"]["flipped"])
            second = next(n for n in event["previews"] if n["rank"] == 2)
            first = next(n for n in event["previews"] if n["rank"] == 1)
            self.assertEqual(event["committed_ids"], second["ids"])
            self.assertEqual(event["retained_ranks"], [1, 3])
            self.assertIn(first["text"], event["memory_text"])
            self.assertNotIn(second["text"], event["memory_text"].split(first["text"], 1)[0])
        self.assertEqual(result["body_ids"], [68, 66, 68, 66, 68, 66, 68, 65])

    def test_lookahead_keeps_rank_one_without_a_better_continuation(self):
        self.lookahead()
        result = self.controlled(RunStore(self.root / "noflip", {}), arm="all_futures")
        self.assertTrue(all(e["selected_rank"] == 1 for e in result["events"]))
        self.assertTrue(all(not e["selection"]["flipped"] for e in result["events"]))
        self.assertEqual(result["body_ids"], [68, 65] * 4)

    def test_filtered_futures_compares_against_the_committed_reference(self):
        self.lookahead()
        seen = []

        def gate(encoder, notes, threshold):
            seen.append([n["rank"] for n in notes])
            return self.keep()

        with self.biased_rollout(), patch("lost_tokens.recurrent_memory.compare_rollouts", gate):
            with (
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
            ):
                result = run_condition(
                    self.model,
                    RunStore(self.root / "gate", {}),
                    self.row,
                    self.cfg,
                    "test",
                    "filtered_futures",
                    lambda _: None,
                )
        self.assertEqual(seen, [[2, 1, 3]] * 3 + [[1, 2, 3]])
        self.assertTrue(all(e["similarity"]["retained_ranks"] == [2, 3] for e in result["events"]))
        # The stub retains rank 2, but rank 2 was committed: it never enters memory.
        self.assertEqual([e["retained_ranks"] for e in result["events"]], [[3]] * 3 + [[2, 3]])

    def test_selected_only_commits_selection_without_memory(self):
        self.lookahead()
        with self.biased_rollout():
            result = self.controlled(RunStore(self.root / "sel", {}), arm="selected_only")
        self.assertEqual(len(result["events"]), 4)
        self.assertEqual([e["selected_rank"] for e in result["events"]], [2, 2, 2, 1])
        for event in result["events"]:
            self.assertEqual(len(event["previews"]), 3)
            self.assertEqual(event["retained_ranks"], [])
            self.assertEqual(event["memory_ids"], [])
            self.assertIsNone(event["similarity"])
        self.assertEqual(result["body_ids"], [68, 66, 68, 66, 68, 66, 68, 65])
        base_len = len(self.model.prompt(instruction(self.row) + self.row["question"]))
        self.assertEqual(result["final_context_length"], base_len + 8)
        self.assertEqual(ARM_CONDITIONS["selected"], "selected_only")

    def test_lookahead_resume_is_identical(self):
        self.lookahead(memory_preamble=PREAMBLE)
        with self.biased_rollout():
            expected = self.controlled(RunStore(self.root / "la-expected", {}), arm="all_futures")
            paused = PausableStore(self.root / "la-resume", {}, stop_after_calls=9)
            with self.assertRaises(RequestedPause):
                self.controlled(paused, arm="all_futures")
            hashes = {p.name: file_digest(p) for p in (paused.path / "checkpoints").glob("*.json")}
            actual = self.controlled(RunStore(paused.path, {}, resume=True), arm="all_futures")
        self.assertEqual(actual["body_ids"], expected["body_ids"])
        self.assertEqual(actual["final_context_sha256"], expected["final_context_sha256"])
        self.assertEqual(
            [e["selection"] for e in actual["events"]], [e["selection"] for e in expected["events"]]
        )
        self.assertEqual(
            [e["selection"]["flipped"] for e in actual["events"]], [True] * 3 + [False]
        )
        for name, digest_value in hashes.items():
            self.assertEqual(file_digest(paused.path / "checkpoints" / name), digest_value)

    def test_audit_passes_with_lookahead_flip_and_preamble(self):
        self.lookahead(memory_preamble=PREAMBLE)
        for arm in ("all_futures", "selected_only"):
            reviewed, result = self.audited(
                arm,
                [
                    patch.object(StreamDecoder, "candidates", self.eligible),
                    patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
                    self.biased_rollout(),
                ],
            )
            self.assertEqual(reviewed["events"], 4)
            self.assertEqual([e["selected_rank"] for e in result["events"]], [2, 2, 2, 1])

    def test_audit_detects_tampered_selection(self):
        from lost_tokens.audit import audit
        from lost_tokens.core import atomic_json, digest

        self.lookahead()
        reviewed, result = self.audited(
            "all_futures",
            [
                patch.object(StreamDecoder, "candidates", self.eligible),
                patch.object(StreamDecoder, "sample", lambda *_: (68, -1.0)),
                self.biased_rollout(),
            ],
        )
        run = self.root / "audit-all_futures"
        for path in (run / "checkpoints").glob("*.json"):
            saved = json.loads(path.read_text())
            if saved["payload"]["label"].endswith("/event-0/complete"):
                saved["payload"]["result"]["selected_rank"] = 1
                saved["payload"]["result"]["selection"]["selected_rank"] = 1
                saved["sha256"] = digest(saved["payload"])
                atomic_json(path, saved)
        with self.assertRaises(AssertionError):
            audit(run, partial=True, model=self.model)

    def test_configuration_validation(self):
        good = dict(LOOKAHEAD)
        bad = [
            ("selection", "beam"),
            ("memory_preamble", ""),
            ("memory_preamble", "   "),
            ("memory_preamble", 3),
            ("memory_preamble", "see <possibilities> above"),
        ]
        bad.append(("selection", "argmax"))  # lookahead settings present while argmax
        for key, value in bad:
            spec = load_spec()
            spec["experiment"][key] = value
            path = self.root / "bad.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError, msg=(key, value)):
                load_spec(path)
        bad_lookahead = [
            None,
            {**good, "extra": 1},
            {**good, "statistic": "perplexity"},
            {**good, "margin": -0.1},
            {**good, "margin": True},
            {**good, "min_tokens": 0},
            {**good, "min_tokens": 64},
        ]
        for value in bad_lookahead:
            spec = load_spec()
            spec["experiment"].update(selection="lookahead", lookahead=value)
            path = self.root / "bad.json"
            path.write_text(json.dumps(spec))
            with self.assertRaises(ValueError, msg=value):
                load_spec(path)
        spec = load_spec()
        spec["experiment"].update(selection="lookahead", lookahead=good, memory_preamble=PREAMBLE)
        path = self.root / "good.json"
        path.write_text(json.dumps(spec))
        load_spec(path)

    def test_default_protocol_is_lookahead_with_64_token_rollouts(self):
        spec = load_spec()
        exp = spec["experiment"]
        self.assertEqual(exp["branch_tokens"], 64)
        self.assertEqual(exp["selection"], "lookahead")
        self.assertEqual(
            exp["lookahead"], {"statistic": "mean_logprob", "margin": 0.1, "min_tokens": 16}
        )
        self.assertTrue(exp["memory_preamble"])
        need = (
            spec["data"]["prompt_limit"]
            + exp["max_output_tokens"]
            + exp["memory_capacity_tokens"]
            + exp["branch_tokens"]
        )
        self.assertLessEqual(need, spec["model"]["max_context_tokens"])


if __name__ == "__main__":
    unittest.main()
