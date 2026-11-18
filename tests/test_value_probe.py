import unittest
from unittest.mock import patch

from lost_tokens.config import load_spec
from lost_tokens.core import derived_seed, digest
from lost_tokens.recurrent_memory import StreamDecoder
from lost_tokens.value_probe import choose_position, decide_probe, exact_arithmetic
import test_knobs as knobs
import test_recurrent_memory as fixture


def decode(ids):
    return "".join(map(chr, ids))


class ValueProbeTests(unittest.TestCase):
    def test_arithmetic_accepts_numeric_expressions_only(self):
        self.assertEqual(exact_arithmetic(r"1,000 + \frac{6}{2} - 3²"), 994)
        for text in ("1,2 + 3", "2/0", "2**256", "a+4", "min(2,3)"):
            with self.subTest(text=text):
                self.assertIsNone(exact_arithmetic(text))

    def test_selects_high_entropy_aligned_value_and_ignores_partial_suffix(self):
        prefix = "\n2+2="
        continuation = "5\n\n- 3*3 = 8\n\n5*5=2"
        other = continuation.index("8")
        preview = {
            "text": continuation,
            "ids": list(map(ord, continuation)),
            "stop_marker": None,
            "entropies": [3.0 if i == other else 1.0 for i in range(len(continuation))],
        }
        tail = list(map(ord, prefix))
        first = choose_position(preview, {"position": "first"}, decode, tail)
        highest = choose_position(preview, {"position": "entropy"}, decode, tail)
        self.assertEqual((first["offset"], first["expected"]), (0, "4"))
        self.assertEqual((highest["offset"], highest["expected"]), (other, "9"))
        kept = preview["ids"][:other]
        samples = [
            {"ids": list(map(ord, value)), "stop_marker": None}
            for value in ("8\n", "9", "9\n", "7\n")
        ]
        decision = decide_probe(highest, kept, samples, decode, {127}, tail)
        self.assertEqual(decision["sample_values"], ["8", None, "9", "7"])
        self.assertEqual(decision["selected_sample"], 2)

    def test_config_enables_only_value_probe(self):
        cfg = load_spec("configs/vllm-ours-entropy-value.json")
        self.assertEqual(
            cfg["experiment"].pop("value_probe"),
            {"samples": 8, "max_per_case": 1, "position": "entropy"},
        )
        self.assertEqual(cfg, load_spec("configs/vllm-ours-blended-memory.json"))


class ValueProbeAuditTests(unittest.TestCase):
    setUpClass = classmethod(fixture.RecurrentTests.setUpClass.__func__)
    setUp = fixture.RecurrentTests.setUp
    audited = knobs.KnobTests.audited

    def test_verified_alternative_commits_exact_tokens_and_audits(self):
        class Encoder:
            def encode(self, texts):
                return [[1.0, 0.0] for _ in texts], sum(map(len, texts))

        text = "DA\n2+2=5\nZZZ" + chr(126) + r"\boxed{2}" + chr(127)
        offset = text.index("5")
        self.cfg["experiment"].update(
            branch_tokens=11,
            max_output_tokens=len(text),
            max_branch_body_tokens=2,
            value_probe={"samples": 2, "max_per_case": 1, "position": "entropy"},
        )
        case_seed = derived_seed(self.cfg["experiment"]["seed"], "smoke/fixture", "cpu")

        def sample(decoder, state, seed):
            index = len(state.generated_ids)
            if index == offset:
                probe_seed = derived_seed(case_seed, digest(state.ids), "value-probe", 0)
                if seed == derived_seed(probe_seed, "rollout", 0):
                    return ord("4"), -1.0
            return ord(text[index]), -1.0

        report, result = self.audited(
            "filtered_futures",
            [
                patch.object(StreamDecoder, "candidates", fixture.RecurrentTests.eligible),
                patch.object(StreamDecoder, "sample", sample),
                patch.object(self.model, "semantic_encoder", Encoder()),
            ],
        )
        self.assertEqual(report["completed_conditions"], 1)
        self.assertTrue(result["correct"])
        event = result["events"][0]
        self.assertEqual(event["value_probe"]["sample_values"], ["4", "5"])
        self.assertEqual(decode(event["committed_ids"]), "A\n2+2=4\nZZZ")
        self.assertEqual(event["previews"][0]["text"], "A\n2+2=5\nZZZ")
