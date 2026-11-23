"""Selective latent inputs and immutable replay of their exact mixture metadata.

Adapted from the equations of SeLaR (Fu and Luo, ACL 2026). No reference
answers, candidate answers or separate verification calls enter the policy.
"""

import math
from pathlib import Path
import json

from .core import digest


def policy(spec):
    from importlib.resources import files

    defaults = json.loads(files("lost_tokens").joinpath("default.json").read_text())[
        "latent_reasoning"
    ]
    value = {**defaults, **spec.get("latent_reasoning", {})}
    if set(value) != set(defaults):
        raise ValueError("Unknown latent policy field")
    if type(value["top_k"]) is not int or value["top_k"] < 2:
        raise ValueError("latent top_k must be at least two")
    for key in ("entropy_threshold", "contrastive_weight"):
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]):
            raise ValueError("Invalid latent " + key)
    if not 0 <= value["entropy_threshold"] <= 1 or value["contrastive_weight"] < 0:
        raise ValueError("Invalid latent threshold/contrastive weight")
    if type(value["checkpoint_tokens"]) is not int or value["checkpoint_tokens"] < 1:
        raise ValueError("Invalid latent checkpoint interval")
    if (
        type(value["protect_math_tokens"]) is not bool
        or value["mixing_precision"] != "float32"
        or value["reasoning_only"] is not True
    ):
        raise ValueError("Unsupported latent precision, guard or phase policy")
    return value


def protected_tokens(model):
    # The authors' public implementation protects numbers, Latin letters and
    # mathematical syntax. Keep the same static guard across all datasets.
    symbols = r"+ - * / ^ = < > \leq \geq \neq \approx \sim \equiv \to \implies \iff ( ) [ ] { } \left( \right) \left[ \right] \left\{ \right\} \begin{pmatrix} \end{pmatrix} \frac \dfrac \sqrt \sqrt[] \in \notin \subset \supset \subseteq \supseteq \cup \cap \emptyset \varnothing \pi \theta \alpha \beta \gamma \delta \epsilon \lambda \mu \nu \sin \cos \tan \arcsin \arccos \arctan \log \ln \exp _ \binom \choose \cdot \dots \ldots \cdots \vdots \ddots \mathbb \mathbf \mathrm \text \mbox \infty \circ \prime \ast \star \triangle \triangleleft \triangleright \perp \parallel \angle \boxed \overline \underline \lceil \rceil \lfloor \rfloor \left \right \mid | \vert \Vert \because \therefore \forall \exists \wedge \vee \neg \sum \prod \int \lim \min \max \arg \deg \gcd \operatorname \cot \cotg \sec \csc".split()
    symbols += [r"\zeta"] + list("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return set(i for text in symbols for i in model.encode(text))


def latent_choice(model, exp, cfg, logits, token, thinking, enabled, protected):
    """Filtered top-k probabilities are saved exactly for input reconstruction."""
    torch = model.torch
    if not enabled or not thinking:
        return {"entropy": 0.0, "soft": False}
    values, indices = torch.topk(
        logits.float() / exp["temperature"], min(exp["top_k"], logits.numel())
    )
    probs = values.softmax(-1)
    probs = probs.masked_fill(probs.cumsum(-1) - probs > exp["top_p"], 0)
    probs = probs / probs.sum()
    count = min(cfg["top_k"], len(probs))
    weights = probs[:count] / probs[:count].sum()
    entropy = float(-(weights * weights.clamp_min(1e-10).log()).sum() / math.log(count))
    ids = indices[:count].tolist()
    soft = bool(
        enabled
        and thinking
        and entropy >= cfg["entropy_threshold"]
        and token not in model.special_ids
        and not any(i in model.special_ids for i in ids)
        and not (cfg["protect_math_tokens"] and token in protected)
    )
    return {
        "entropy": entropy,
        "soft": soft,
        **(
            {
                "ids": ids,
                "weights": weights.tolist(),
                "strength": cfg["contrastive_weight"] * entropy,
            }
            if soft
            else {}
        ),
    }


def mix_embeddings(torch, embedding, rows):
    """One vector operation, no additional transformer pass or sibling KV."""
    ids = torch.tensor([r["ids"] for r in rows], dtype=torch.long, device=embedding.device)
    weights = torch.tensor(
        [r["weights"] for r in rows], dtype=torch.float32, device=embedding.device
    )
    e = embedding[ids].float()
    mixed = (weights.unsqueeze(-1) * e).sum(1)
    strength = torch.tensor(
        [r["strength"] for r in rows], dtype=torch.float32, device=embedding.device
    )
    return (mixed + strength.unsqueeze(-1) * (mixed - e[:, 0])).to(embedding.dtype)


class LatentTrace:
    """A content-addressed chain of tokens AND input-mixture descriptors."""

    def __init__(self, store, tag, prompt, cfg, mode):
        self.store, self.tag, self.cfg = store, tag, cfg
        self.root = digest({"prompt": prompt, "policy": cfg, "mode": mode})
        self.ids, self.records = [], []
        self.terminal = False
        self.blocks = 0
        self.restore()

    def request(self):
        return {
            "previous": self.root,
            "body_position": len(self.ids),
            "checkpoint_tokens": self.cfg["checkpoint_tokens"],
        }

    def label(self):
        return self.tag + f"/latent-block-{self.blocks}"

    def restore(self):
        while True:
            request, label = self.request(), self.label()
            path = (
                self.store.path
                / "checkpoints"
                / (digest({"label": label, "request": request}) + ".json")
            )
            if not path.exists():
                self.check_tail()
                return
            saved = self.store.call(
                label,
                request,
                lambda: (_ for _ in ()).throw(RuntimeError("Missing saved latent block")),
            )
            self.accept(saved)
            if self.terminal:
                self.check_tail()
                return

    def check_tail(self):
        # Each trajectory has its own RunStore. A broken chain must never be
        # mistaken for an unfinished prefix and silently regenerated.
        if len(list((self.store.path / "checkpoints").glob("*.json"))) != self.blocks:
            raise ValueError("Unreachable or extra latent checkpoints")

    def accept(self, block):
        if (
            len(block["ids"]) != len(block["records"])
            or not block["ids"]
            or len(block["ids"]) > self.cfg["checkpoint_tokens"]
        ):
            raise ValueError("Invalid latent checkpoint block")
        if len(block["ids"]) != self.cfg["checkpoint_tokens"] and not block["terminal"]:
            raise ValueError("Incomplete nonterminal latent checkpoint")
        self.ids.extend(block["ids"])
        self.records.extend(block["records"])
        self.root = digest({"previous": self.root, "block": block})
        self.terminal = block["terminal"]
        self.blocks += 1

    def append(self, ids, records, terminal=False):
        block = {"ids": list(ids), "records": list(records), "terminal": bool(terminal)}
        result = self.store.call(self.label(), self.request(), lambda: block)
        if result != block:
            raise ValueError("Existing latent block differs from newly generated data")
        self.accept(result)


def validate_record(record, cfg, special_ids, protected, thinking, enabled):
    entropy = record["entropy"]
    if not math.isfinite(entropy) or not -1e-6 <= entropy <= 1.000001:
        raise ValueError("Invalid recorded entropy")
    token = record["token"]
    if record["soft"]:
        ids, weights = record["ids"], record["weights"]
        if (
            not (enabled and thinking)
            or token in special_ids
            or (cfg["protect_math_tokens"] and token in protected)
            or any(i in special_ids for i in ids)
        ):
            raise ValueError("Latent embedding outside permitted thinking positions")
        if (
            len(ids) != cfg["top_k"]
            or len(set(ids)) != len(ids)
            or len(weights) != len(ids)
            or any(not math.isfinite(x) or x < 0 for x in weights)
            or abs(sum(weights) - 1) > 1e-5
        ):
            raise ValueError("Invalid latent candidate mixture")
        h = -sum(x * math.log(max(x, 1e-10)) for x in weights) / math.log(len(weights))
        if (
            abs(h - entropy) > 1e-5
            or entropy < cfg["entropy_threshold"]
            or abs(record["strength"] - cfg["contrastive_weight"] * entropy) > 1e-6
        ):
            raise ValueError("Latent policy metadata differs")
