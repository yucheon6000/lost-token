"""Latent gate math, request isolation, immutable replay and baseline invariance."""

import copy
from dataclasses import dataclass
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest

import torch

from lost_tokens.core import RunStore, atomic_json, digest, file_digest, derived_seed
from lost_tokens.config import load_spec
from lost_tokens.latent import policy, latent_choice, mix_embeddings, LatentTrace, validate_record
from lost_tokens.latent_vllm import LatentInputHook, LatentProcessor, Work
from lost_tokens.recurrent_memory import StreamDecoder, StreamState
import test_recurrent_memory as tiny


class LatentTests(unittest.TestCase):
    setUpClass = classmethod(tiny.RecurrentTests.setUpClass.__func__)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = load_spec()
        self.pol = policy(self.cfg)
        self.model.protected = set()

    def test_gate_keeps_final_special_math_and_baseline_discrete(self):
        logits = torch.zeros(128)
        exp = self.cfg["experiment"]
        r = latent_choice(self.model, exp, self.pol, logits, 65, True, True, set())
        self.assertTrue(r["soft"])
        self.assertAlmostEqual(sum(r["weights"]), 1, places=6)
        for token, thinking, enabled, protected in [
            (65, False, True, set()),
            (65, True, False, set()),
            (126, True, True, set()),
            (65, True, True, {65}),
        ]:
            self.assertFalse(
                latent_choice(
                    self.model, exp, self.pol, logits, token, thinking, enabled, protected
                )["soft"]
            )
        logits = torch.full((128,), -100.0)
        logits[65] = 100
        self.assertFalse(
            latent_choice(self.model, exp, self.pol, logits, 65, True, True, set())["soft"]
        )

    def test_contrastive_mix_matches_equation_and_is_row_local(self):
        e = torch.arange(32, dtype=torch.float32).reshape(8, 4)
        r = {"ids": [1, 2, 3], "weights": [0.5, 0.3, 0.2], "strength": 0.8}
        m = 0.5 * e[1] + 0.3 * e[2] + 0.2 * e[3]
        result = mix_embeddings(torch, e, [r])
        torch.testing.assert_close(result[0], m + 0.8 * (m - e[1]), rtol=0, atol=1e-6)
        self.assertEqual(result.dtype, e.dtype)

    def test_input_hook_maps_mixed_prefill_and_decode_without_cross_case_leakage(self):
        embed = torch.nn.Embedding(128, 4)

        class Runner:
            model = SimpleNamespace(model=SimpleNamespace(embed_tokens=embed))

            def execute_model(self, inputs):
                return embed(inputs.input_tokens)

        record = {"ids": [1, 2, 3], "weights": [0.5, 0.3, 0.2], "strength": 0.8}
        a = SimpleNamespace(soft={3: record}, applied=set())
        b = SimpleNamespace(soft={}, applied=set())
        runner = Runner()
        hook = LatentInputHook(
            runner, {"a": SimpleNamespace(processor=a), "b": SimpleNamespace(processor=b)}
        )
        inp = SimpleNamespace(
            request_ids_to_seq_ids={"a": [1], "b": [2]},
            query_lens=[2, 1],
            seq_lens=[5, 7],
            input_tokens=torch.tensor([4, 5, 6]),
        )
        expected = embed(inp.input_tokens).detach().clone()
        got = runner.execute_model(inp)
        torch.testing.assert_close(got[0], mix_embeddings(torch, embed.weight, [record])[0])
        torch.testing.assert_close(got[1:], expected[1:], rtol=0, atol=0)
        self.assertEqual(a.applied, {3})
        self.assertEqual(b.applied, set())
        self.assertEqual(hook.selected, [])
        hook.handle.remove()

    def test_trace_replays_same_mixtures_and_never_rewrites_saved_blocks(self):
        pol = {**self.pol, "checkpoint_tokens": 2}
        store = RunStore(self.root / "trace", {})
        t = LatentTrace(store, "trajectory", [1], pol, "selar")
        records = [
            {"token": 65, "soft": False, "entropy": 0, "seed": 4},
            {
                "token": 66,
                "soft": True,
                "entropy": 1,
                "seed": 5,
                "ids": [2, 3, 4],
                "weights": [1 / 3] * 3,
                "strength": 1,
            },
        ]
        t.append([65, 66], records)
        hashes = {p.name: file_digest(p) for p in (store.path / "checkpoints").glob("*.json")}
        re = LatentTrace(RunStore(store.path, {}, resume=True), "trajectory", [1], pol, "selar")
        self.assertEqual(re.ids, t.ids)
        self.assertEqual(re.records, t.records)
        self.assertEqual(re.root, t.root)
        re.append([127], [{"token": 127, "soft": False, "entropy": 0, "seed": 6}], True)
        for name, sha in hashes.items():
            self.assertEqual(file_digest(store.path / "checkpoints" / name), sha)
        # A rehashed but altered first block cannot silently orphan later blocks.
        p = next(
            p
            for p in (store.path / "checkpoints").glob("*.json")
            if json.loads(p.read_text())["payload"]["request"]["body_position"] == 0
        )
        saved = json.loads(p.read_text())
        saved["payload"]["result"]["records"][1]["weights"] = [0.5, 0.25, 0.25]
        saved["sha256"] = digest(saved["payload"])
        atomic_json(p, saved)
        with self.assertRaisesRegex(ValueError, "Unreachable"):
            LatentTrace(RunStore(store.path, {}, resume=True), "trajectory", [1], pol, "selar")

    def test_discrete_processor_samples_exact_original_ar_position_seeds(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["experiment"]["max_output_tokens"] = 4
        cfg["experiment"]["checkpoint_body_tokens"] = 4
        pol = policy(cfg)
        prompt = [1]
        seed = 17
        trace = LatentTrace(RunStore(self.root / "ar", {}), "trajectory", prompt, pol, "ar")
        processor = LatentProcessor(self.model, cfg["experiment"], pol, prompt, trace, seed, False)
        decoder = StreamDecoder(self.model, cfg["experiment"])
        for i in range(4):
            logits = torch.linspace(-2, 2, 128)
            logits[126:] = -100
            state = StreamState(prompt + processor.ids, None, logits, processor.ids)
            expected, _ = decoder.sample(state, derived_seed(seed, "body", i))
            processor(list(processor.ids), logits.clone())
            self.assertEqual(processor.ids[-1], expected)
        self.assertTrue(trace.terminal)
        self.assertFalse(processor.soft)

    def test_incomplete_resume_teacher_forces_original_token_and_saved_soft_input(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["experiment"]["max_output_tokens"] = 4
        pol = {**policy(cfg), "checkpoint_tokens": 2}
        store = RunStore(self.root / "replay", {})
        seed = 19
        prompt = [1]
        trace = LatentTrace(store, "trajectory", prompt, pol, "selar")
        r = [
            {
                "token": 65,
                "soft": True,
                "entropy": 1,
                "ids": [2, 3, 4],
                "weights": [1 / 3] * 3,
                "strength": 1,
                "seed": derived_seed(seed, "body", 0),
            },
            {"token": 66, "soft": False, "entropy": 0, "seed": derived_seed(seed, "body", 1)},
        ]
        trace.append([65, 66], r)
        p = LatentProcessor(self.model, cfg["experiment"], pol, prompt, trace, seed, True)
        for token in [65, 66]:
            logits = torch.zeros(128)
            logits[90] = 100
            p(list(p.ids), logits)
            self.assertEqual(p.ids[-1], token)
        self.assertEqual(len(trace.ids), 2)
        self.assertEqual(p.history, [1, 65, 66])
        self.assertIn(1, p.soft)

    def test_invalid_metadata_and_policy_are_rejected(self):
        r = {
            "token": 65,
            "soft": True,
            "entropy": 1,
            "ids": [2, 3, 4],
            "weights": [1 / 3] * 3,
            "strength": 1,
        }
        validate_record(r, self.pol, {126}, set(), True, True)
        for bad in [
            {**r, "weights": [0.7, 0.3, 0.3]},
            {**r, "strength": 0},
            {**r, "entropy": float("nan")},
        ]:
            with self.assertRaises(ValueError):
                validate_record(bad, self.pol, {126}, set(), True, True)
        with self.assertRaises(ValueError):
            policy({"latent_reasoning": {"entropy_threshold": float("nan")}})
        with self.assertRaises(ValueError):
            policy({"latent_reasoning": {"checkpoint_tokens": True}})


if __name__ == "__main__":
    unittest.main()
