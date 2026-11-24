"""Single-trajectory EM-INF with analytic logit gradients and per-token Adam.

The reference optimizer is entropy + beta*KL(p_original || p_new), before
temperature/top-k/top-p. Only a detached output vector is updated, never weights
or KV inputs. Adam moments reset for each token, as in the authors' implementation.
"""

import json
import math
from importlib.resources import files

from .core import derived_seed
from .latent_vllm import LatentProcessor, LatentModel
from .recurrent_memory import StreamState, emitted_marker


def policy(spec):
    defaults = json.loads(files("lost_tokens").joinpath("default.json").read_text())["em_inf"]
    cfg = {**defaults, **spec.get("em_inf", {})}
    if set(cfg) != set(defaults):
        raise ValueError("Unknown EM-INF policy field")
    for key in ("threshold", "kl_weight", "learning_rate"):
        if type(cfg[key]) not in (int, float) or not math.isfinite(cfg[key]):
            raise ValueError("Invalid EM-INF " + key)
    if cfg["threshold"] < 0 or cfg["kl_weight"] < 0 or cfg["learning_rate"] <= 0:
        raise ValueError("Invalid EM-INF optimizer limits")
    for key in ("n_grad_steps", "checkpoint_tokens"):
        if type(cfg[key]) is not int or cfg[key] < 1:
            raise ValueError("Invalid EM-INF " + key)
    if type(cfg["compiled"]) is not bool or cfg["scope"] != "all_tokens":
        raise ValueError("Unsupported EM-INF execution/scope")
    return cfg


def optimize_logits(logits, threshold, kl_weight, learning_rate, n_grad_steps):
    """Equivalent to fresh Adam on the authors' detached FP32 output logits.

    Tensor-only early stopping allows kernel compilation without a host sync at
    every gradient step. Masked/padded vocabulary entries always remain masked.
    The function supports a single vocabulary vector or independent batch rows.
    """
    import torch

    z = logits.float().clone()
    finite = torch.isfinite(z)
    original = z.softmax(-1)
    m, v = torch.zeros_like(z), torch.zeros_like(z)
    before = -(original * (original + 1e-12).log()).sum(-1, keepdim=True)
    active = torch.ones_like(before, dtype=torch.bool)
    steps = torch.zeros_like(before)
    for index in range(1, n_grad_steps + 1):
        p = z.softmax(-1)
        logp = (p + 1e-12).log()
        h = -(p * logp).sum(-1, keepdim=True)
        active = active & (h >= threshold)
        # d[-sum(p*log(p+eps))]/dz, plus reverse KL used by F.kl_div
        # in the reference (target=original, input=log(p_new)).
        dh_dp = -(logp + p / (p + 1e-12))
        grad = p * (dh_dp - (p * dh_dp).sum(-1, keepdim=True))
        grad = grad + kl_weight * (p - original)
        m = 0.9 * m + 0.1 * grad
        v = 0.999 * v + 0.001 * grad.square()
        denom = (v / (1 - 0.999**index)).sqrt() + 1e-8
        delta = learning_rate * (m / (1 - 0.9**index)) / denom
        z = torch.where(active & finite, z - delta, z)
        steps = steps + active.to(steps.dtype)
    after = z.softmax(-1)
    entropy_after = -(after * (after + 1e-12).log()).sum(-1, keepdim=True)
    change = torch.where(finite, (z - logits).abs(), 0).amax(-1, keepdim=True)
    return z, torch.cat((before, entropy_after, steps, change), dim=-1)


class EMTransform:
    def __init__(self, cfg):
        self.cfg = cfg
        self.kernel = optimize_logits
        if cfg["compiled"]:
            import torch

            self.kernel = torch.compile(
                optimize_logits,
                fullgraph=True,
                dynamic=False,
                options={"triton.cudagraphs": False},
            )

    def __call__(self, logits):
        c = self.cfg
        return self.kernel(
            logits, c["threshold"], c["kl_weight"], c["learning_rate"], c["n_grad_steps"]
        )


class EMModel(LatentModel):
    def __init__(self, cfg, em_cfg, log=print):
        super().__init__(cfg, log)
        self.em_transform = EMTransform(em_cfg)
        # Compile before submitting requests to avoid counting cold compilation
        # as decoder throughput, or racing compiler initialization across cases.
        import torch

        with torch.inference_mode():
            vocab_size = self.engine.llm.llm_engine.model_config.hf_config.vocab_size
            probe = torch.linspace(-3, 3, vocab_size, device=self.device)
            self.em_transform(probe)
            torch.cuda.synchronize(self.device)


class EMProcessor(LatentProcessor):
    """Reuse the audited continuous engine, with exclusively discrete inputs."""

    def __call__(self, output_ids, logits):
        if list(output_ids) != self.ids or self.done:
            raise RuntimeError("EM-INF request token/termination mismatch")
        pos = len(self.ids)
        step_seed = derived_seed(self.seed, "body", pos)
        if pos < self.start:
            record = self.trace.records[pos]
            if record["seed"] != step_seed:
                raise ValueError("Stored EM-INF replay seed changed")
            token = record["token"]
        else:
            raw = logits.float()
            if self.enabled:
                adjusted, stats = self.model.em_transform(raw)
            else:
                adjusted, stats = raw, None
            state = StreamState(self.history, None, adjusted, self.ids)
            token, sampled_lp = self.decoder.sample(state, step_seed)
            before, after, steps, change = (
                stats.cpu().tolist() if stats is not None else (0, 0, 0, 0)
            )
            record = {
                "token": token,
                "seed": step_seed,
                "soft": False,
                "entropy": 0.0,
                "entropy_before": before,
                "entropy_after": after,
                "optimization_steps": int(steps),
                "max_logit_change": change,
                "logprob": float(raw.log_softmax(-1)[token]),
                "optimized_logprob": sampled_lp,
            }
            self.records.append(record)
            self.pending.append(token)
            self.pending_records.append(record)
        marker = emitted_marker(self.model, self.history, token)
        self.history.append(token)
        self.ids.append(token)
        if marker:
            self.thinking = not marker.startswith("</")
        if pos >= self.start:
            self.done = token in self.model.eos_ids or pos + 1 >= self.exp["max_output_tokens"]
            if len(self.pending) == self.cfg["checkpoint_tokens"] or self.done:
                self.trace.append(self.pending, self.pending_records, self.done)
                self.pending, self.pending_records = [], []
        logits.fill_(-self.model.torch.inf)
        logits[token] = 0
        return logits


def validate_record(record, cfg, enabled):
    if record["soft"]:
        raise ValueError("EM-INF must not inject soft embeddings")
    for key in ("entropy_before", "entropy_after", "max_logit_change"):
        if not math.isfinite(record[key]) or record[key] < -1e-6:
            raise ValueError("Invalid EM-INF optimizer metadata")
    steps = record["optimization_steps"]
    if type(steps) is not int or not 0 <= steps <= cfg["n_grad_steps"]:
        raise ValueError("Invalid EM-INF step count")
    if not enabled and any(
        record[k] != 0
        for k in ("entropy_before", "entropy_after", "optimization_steps", "max_logit_change")
    ):
        raise ValueError("Optimizer altered the AR control")
    if steps and record["entropy_before"] < cfg["threshold"] - 1e-6:
        raise ValueError("Optimizer ignored the entropy stopping threshold")
    # Adam normalizes each coordinate; this conservative bound catches corrupt
    # descriptors without assuming entropy must monotonically fall under KL.
    if record["max_logit_change"] > cfg["learning_rate"] * cfg["n_grad_steps"] * 2 + 1e-4:
        raise ValueError("EM-INF recorded an impossible optimizer displacement")
