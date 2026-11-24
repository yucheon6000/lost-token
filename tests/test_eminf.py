"""Logit-only Adam equivalence, masked vocabulary, AR invariance and resume."""

import copy
from pathlib import Path
import tempfile
import unittest

import torch
import torch.nn.functional as F

from lost_tokens.config import load_spec
from lost_tokens.core import RunStore, derived_seed
from lost_tokens.eminf import policy, optimize_logits, EMTransform, EMProcessor, validate_record
from lost_tokens.latent import LatentTrace
from lost_tokens.recurrent_memory import StreamDecoder, StreamState
import test_recurrent_memory as tiny


def reference(raw, cfg):
    z = torch.nn.Parameter(raw.float().reshape(1, -1).clone())
    p0 = z.detach().softmax(-1)
    opt = torch.optim.Adam([z], lr=cfg["learning_rate"])
    for _ in range(cfg["n_grad_steps"]):
        opt.zero_grad()
        p = z.softmax(-1)
        h = -(p * (p + 1e-12).log()).sum()
        if h < cfg["threshold"]:
            break
        loss = h + cfg["kl_weight"] * F.kl_div(p.log(), p0, reduction="batchmean")
        loss.backward()
        opt.step()
    return z.detach().reshape_as(raw)


class EMTests(unittest.TestCase):
    setUpClass = classmethod(tiny.RecurrentTests.setUpClass.__func__)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="temp/diagnostics")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cfg = load_spec()
        self.pol = {**policy(self.cfg), "compiled": False, "checkpoint_tokens": 2}
        self.model.protected = set()
        self.model.em_transform = EMTransform(self.pol)

    def test_analytic_kernel_matches_official_autograd_adam(self):
        for scale in (0.2, 1, 5):
            raw = torch.linspace(-3, 3, 128) * scale
            actual, stats = self.model.em_transform(raw)
            torch.testing.assert_close(actual, reference(raw, self.pol), rtol=1e-6, atol=2e-6)
            self.assertLessEqual(stats[1], stats[0] + 1e-6)
            self.assertEqual(int(stats[2]), 3)
            self.assertTrue(torch.equal(raw, torch.linspace(-3, 3, 128) * scale))

    def test_threshold_masked_logits_and_independent_rows(self):
        confident = torch.full((128,), -100.0)
        confident[65] = 100
        got, stats = self.model.em_transform(confident)
        torch.testing.assert_close(got, confident, rtol=0, atol=0)
        self.assertEqual(int(stats[2]), 0)
        raw = torch.linspace(-2, 2, 128)
        raw[-4:] = -torch.inf
        got, stats = self.model.em_transform(raw)
        self.assertTrue(torch.isneginf(got[-4:]).all())
        self.assertTrue(torch.isfinite(got[:-4]).all())
        rows, rs = self.model.em_transform(torch.stack((confident, raw)))
        torch.testing.assert_close(rows[0], confident, rtol=0, atol=0)
        torch.testing.assert_close(rows[1], got, rtol=0, atol=0)
        self.assertEqual(int(rs[0, 2]), 0)
        self.assertEqual(int(rs[1, 2]), 3)

    def test_disabled_processor_is_exact_original_ar_and_never_soft(self):
        exp = {**self.cfg["experiment"], "max_output_tokens": 5}
        trace = LatentTrace(RunStore(self.root / "ar", {}), "trajectory", [1], self.pol, "ar")
        proc = EMProcessor(self.model, exp, self.pol, [1], trace, 17, False)
        decoder = StreamDecoder(self.model, exp)
        for pos in range(5):
            logits = torch.linspace(-2, 2, 128)
            logits[126:] = -100
            want, _ = decoder.sample(
                StreamState([1] + proc.ids, None, logits, proc.ids), derived_seed(17, "body", pos)
            )
            proc(list(proc.ids), logits.clone())
            self.assertEqual(proc.ids[-1], want)
            validate_record(proc.records[-1], self.pol, False)
        self.assertTrue(trace.terminal)
        self.assertFalse(proc.soft)

    def test_resume_teacher_forces_exact_saved_tokens_and_reuses_metadata(self):
        exp = {**self.cfg["experiment"], "max_output_tokens": 5}

        def logits(pos):
            x = torch.linspace(-2, 2, 128) + torch.sin(torch.arange(128) + pos)
            x[126:] = -100
            return x

        def make(path, resume=False):
            t = LatentTrace(RunStore(path, {}, resume=resume), "trajectory", [1], self.pol, "eminf")
            return t, EMProcessor(self.model, exp, self.pol, [1], t, 19, True)

        whole, p = make(self.root / "whole")
        for i in range(5):
            p(list(p.ids), logits(i))
        partial, q = make(self.root / "resume")
        for i in range(2):
            q(list(q.ids), logits(i))
        saved = copy.deepcopy(partial.records)
        resumed, r = make(self.root / "resume", True)
        for i in range(5):
            r(list(r.ids), logits(i))
        self.assertEqual(resumed.ids, whole.ids)
        self.assertEqual(resumed.records, whole.records)
        self.assertEqual(resumed.records[:2], saved)
        self.assertEqual(resumed.root, whole.root)
        self.assertFalse(r.soft)

    def test_policy_and_receipt_reject_invalid_optimizer_identity(self):
        for update in (
            {"threshold": float("nan")},
            {"learning_rate": 0},
            {"n_grad_steps": True},
            {"scope": "reasoning"},
            {"unexpected": 1},
        ):
            with self.assertRaises(ValueError):
                policy({"em_inf": update})
        receipt = {
            "soft": False,
            "entropy_before": 1.0,
            "entropy_after": 0.9,
            "optimization_steps": 3,
            "max_logit_change": 0.3,
        }
        validate_record(receipt, self.pol, True)
        for update in (
            {"soft": True},
            {"max_logit_change": 10},
            {"optimization_steps": 4},
            {"entropy_after": float("nan")},
        ):
            with self.assertRaises(ValueError):
                validate_record({**receipt, **update}, self.pol, True)
        with self.assertRaises(ValueError):
            validate_record(receipt, self.pol, False)


if __name__ == "__main__":
    unittest.main()
