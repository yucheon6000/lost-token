import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

from lost_tokens.config import load_spec
from lost_tokens.core import derived_seed
from lost_tokens.core import RunStore
from lost_tokens.recurrent_memory import StreamDecoder, StreamState, run_condition
from lost_tokens.vllm_backend import ProtocolProcessor, VLLMStreamDecoder
from test_recurrent_memory import ThinkingTokenizer


class VLLMProtocolTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        tokenizer = ThinkingTokenizer()
        self.model = SimpleNamespace(
            torch=torch,
            device=torch.device("cpu"),
            tokenizer=tokenizer,
            encode=lambda text: tokenizer.encode(text),
            decode=lambda ids: tokenizer.decode(ids),
            eos_ids={127},
            special_ids={1, 126, 127},
            _check=lambda *args: None,
        )
        self.exp = load_spec()["experiment"]
        self.root = StreamState([1, 65], None, None, [65])

    @staticmethod
    def logits(tokens):
        scores = torch.full((128,), -20.0)
        for token, value in tokens.items():
            scores[token] = value
        return scores

    def step(self, processor, scores):
        return int(processor(list(processor.ids), scores.clone()).argmax())

    def test_fork_stops_before_sampling_and_does_not_consume_body(self):
        p = ProtocolProcessor(self.model, self.exp, self.root, 8, 12, 1, True)
        self.assertEqual(self.step(p, self.logits({65: 0.0, 66: -0.1})), 127)
        self.assertEqual(p.ids, [])
        self.assertTrue(p.fork["eligible"])
        self.assertEqual(p.checks[0]["body_position"], 1)
        self.assertEqual(self.root.ids, [1, 65])

    def test_sampling_matches_original_per_position_seed_and_raw_logprob(self):
        scores = self.logits({65: 0.2, 66: 0.1, 67: 0.0})
        p = ProtocolProcessor(self.model, self.exp, self.root, 3, 91, 100)
        for index in range(3):
            state = StreamState(
                self.root.ids + p.ids, None, scores, self.root.generated_ids + p.ids
            )
            token, lp = StreamDecoder(self.model, self.exp).sample(
                state, derived_seed(91, "body", 100 + index)
            )
            self.assertEqual(self.step(p, scores), token)
            self.assertAlmostEqual(p.logprobs[-1], lp)
        self.assertEqual(self.step(p, scores), 127)
        self.assertEqual(len(p.ids), 3)

    def test_forced_rollout_first_token_and_seed_are_preserved(self):
        scores = self.logits({65: 0.2, 66: 0.1, 67: 0.0})
        p = ProtocolProcessor(self.model, self.exp, self.root, 3, 51, first=66)
        self.assertEqual(self.step(p, scores), 66)
        state = StreamState(self.root.ids + p.ids, None, scores, self.root.generated_ids + p.ids)
        token, _ = StreamDecoder(self.model, self.exp).sample(state, derived_seed(51, "rollout", 1))
        self.assertEqual(self.step(p, scores), token)
        self.assertEqual(len(p.entropies), 2)

    def test_guard_uses_body_history_and_never_blocks_termination(self):
        self.root.generated_ids = [65] * 64
        p = ProtocolProcessor(self.model, self.exp, self.root, 2, 91)
        self.assertNotEqual(self.step(p, self.logits({65: 1.0, 66: 0.0})), 65)
        self.assertEqual(p.guards[0]["blocked_token"], 65)
        self.root.generated_ids = [126] * 64
        p = ProtocolProcessor(self.model, self.exp, self.root, 2, 91)
        self.assertEqual(self.step(p, self.logits({126: 10.0})), 126)
        self.assertEqual(p.marker, "</think>")
        self.assertEqual(self.step(p, self.logits({65: 10.0})), 127)
        self.assertEqual(p.ids, [126])

    def test_divergent_engine_history_is_rejected(self):
        p = ProtocolProcessor(self.model, self.exp, self.root, 2, 91)
        with self.assertRaisesRegex(RuntimeError, "diverged"):
            p([66], self.logits({65: 1.0}))

    def test_advance_keeps_memory_out_of_generated_history(self):
        state = copy.deepcopy(self.root)
        decoder = VLLMStreamDecoder(self.model, self.exp)
        decoder.advance(state, [70, 71])
        decoder.advance(state, [72], generated=True)
        self.assertEqual(state.ids, [1, 65, 70, 71, 72])
        self.assertEqual(state.generated_ids, [65, 72])
        self.assertEqual(self.root.ids, [1, 65])

    def test_whole_memory_protocol_matches_reference_and_checkpoint_replay(self):
        scores = self.logits({65: 0.2, 66: 0.1})
        self.model.model = lambda **kwargs: SimpleNamespace(
            past_key_values=None, logits=scores.reshape(1, 1, -1).clone()
        )
        self.model._sync = lambda: None
        self.model.log = lambda *args: None
        self.model.prompt = lambda text: self.model.encode(text) + [1]
        model = self.model

        class Engine:
            def submit(self, p):
                for _ in range(p.count + 1):
                    token = int(p(list(p.ids), scores.clone()).argmax())
                    if token in model.eos_ids:
                        break
                return p

        self.model.engine = Engine()
        cfg = load_spec()
        cfg["experiment"].update(
            max_output_tokens=48,
            branch_tokens=8,
            checkpoint_body_tokens=7,
            min_branch_interval_tokens=12,
            selection="argmax",
            lookahead=None,
        )
        row = {
            "id": "one",
            "task": "aime25",
            "question": "Compute.",
            "answer_format": "math",
            "gold": "2",
            "choices": [],
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            expected = run_condition(
                model,
                RunStore(root / "hf", {}),
                row,
                cfg,
                "evaluation/aime25",
                "all_futures",
                lambda _: None,
            )
            with patch("lost_tokens.recurrent_memory.StreamDecoder", VLLMStreamDecoder):
                actual = run_condition(
                    model,
                    RunStore(root / "vllm", {}),
                    row,
                    cfg,
                    "evaluation/aime25",
                    "all_futures",
                    lambda _: None,
                )
                replay = run_condition(
                    model,
                    RunStore(root / "vllm", {}, resume=True),
                    row,
                    cfg,
                    "evaluation/aime25",
                    "all_futures",
                    lambda _: None,
                )
            self.assertGreater(len(actual["events"]), 1)
            self.assertTrue(any(e["memory_ids"] for e in actual["events"]))
            self.assertEqual(expected["body_ids"], actual["body_ids"])
            for key in ("body_ids", "events", "final_context_sha256", "retained_memory_events"):
                self.assertEqual(actual[key], replay[key])
            for a, b in zip(expected["events"], actual["events"]):
                for key in ("body_position", "root_sha256", "committed_ids", "memory_ids"):
                    self.assertEqual(a[key], b[key])
