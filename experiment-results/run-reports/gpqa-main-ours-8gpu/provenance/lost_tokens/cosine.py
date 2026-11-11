"""Frozen rollout embeddings and auditable cosine-based candidate retention."""

from __future__ import annotations

import time


class CosineEncoder:
    """Qwen3-Embedding last-token pooling, as in its official Transformers example.

    Inputs are rollout strings only, with no shared question/prefix, labels, gold,
    or instruction added. No truncation is allowed. CPU execution avoids competing
    with the independent generation KV copies for GPU memory.
    """

    def __init__(self, cfg):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.cfg, self.torch = cfg, torch
        kwargs = {k: cfg[k] for k in ("revision", "cache_dir", "local_files_only")}
        kwargs.update(token=False, trust_remote_code=False)
        self.tokenizer = AutoTokenizer.from_pretrained(cfg["name"], padding_side="left", **kwargs)
        self.model = (
            AutoModel.from_pretrained(
                cfg["name"],
                dtype=getattr(torch, cfg["dtype"]),
                attn_implementation="sdpa",
                **kwargs,
            )
            .to(cfg["device"])
            .eval()
        )
        self.model.requires_grad_(False)

    def encode(self, texts):
        if not texts or any(not t.strip() for t in texts):
            raise ValueError("Empty embedding input")
        vectors = []
        tokens_count = 0
        for start in range(0, len(texts), self.cfg["batch_size"]):
            tokens = self.tokenizer(
                texts[start : start + self.cfg["batch_size"]],
                padding=True,
                truncation=False,
                return_tensors="pt",
            )
            if tokens["input_ids"].shape[1] > self.cfg["max_tokens"]:
                raise ValueError("Encoder length exceeded; refusing silent truncation")
            tokens_count += int(tokens["attention_mask"].sum())
            tokens = {k: v.to(self.cfg["device"]) for k, v in tokens.items()}
            with self.torch.inference_mode():
                hidden = self.model(**tokens, use_cache=False).last_hidden_state
                # Left padding makes the final position the final real token.
                assert bool(tokens["attention_mask"][:, -1].all())
                pooled = hidden[:, -1].float()
                normalized = self.torch.nn.functional.normalize(pooled, p=2, dim=-1)
            vectors.extend(normalized.cpu().tolist())
        return vectors, tokens_count


def cosine_matrix(vectors):
    """Compute actual normalized dot products from retained float vectors."""
    import torch

    v = torch.tensor(vectors, dtype=torch.float64)
    if v.ndim != 2 or not len(v) or not bool(torch.isfinite(v).all()):
        raise ValueError("Invalid embedding matrix")
    norm = v.norm(dim=1, keepdim=True)
    if bool((norm <= 0).any()):
        raise ValueError("Zero embeddings cannot define cosine similarity")
    v = v / norm
    scores = (v @ v.T).clamp(-1, 1)
    scores.fill_diagonal_(1.0)
    return scores.tolist()


def select_distinct(ranks, matrix, valid, threshold):
    """Greedy by probability rank; compare each option to all retained options."""
    if not -1 <= threshold <= 1:
        raise ValueError("Cosine threshold outside [-1, 1]")
    retained = [0] if valid and valid[0] else []
    decisions = []
    for index in range(1, len(ranks)):
        if not retained or not valid[index]:
            decisions.append(
                {
                    "rank": ranks[index],
                    "drop_alternative": True,
                    "reason": "empty_reference_or_fragment",
                    "compared_ranks": [],
                    "closest_rank": None,
                    "max_cosine": None,
                }
            )
            continue
        closest = max(retained, key=lambda j: matrix[index][j])
        score = matrix[index][closest]
        drop = score >= threshold
        decisions.append(
            {
                "rank": ranks[index],
                "drop_alternative": drop,
                "reason": "cosine_above_threshold" if drop else "cosine_below_threshold",
                "compared_ranks": [ranks[j] for j in retained],
                "closest_rank": ranks[closest],
                "max_cosine": score,
            }
        )
        if not drop:
            retained.append(index)
    # A reference without any distinct alternative supplies no discarded future.
    # The selected reference is committed to the body, never listed as a possibility.
    return [ranks[i] for i in retained if i != 0], decisions


def compare_rollouts(encoder, notes, threshold):
    started = time.monotonic()
    texts = [n["text"] for n in notes]
    valid = [bool(t.strip()) for t in texts]
    ranks = [n["rank"] for n in notes]
    if not ranks or len(set(ranks)) != len(ranks):
        raise ValueError("Require unique ranks; the first entry is the committed reference")
    indices = [i for i, v in enumerate(valid) if v]
    vectors, tokens = encoder.encode([texts[i] for i in indices]) if indices else ([], 0)
    dense = cosine_matrix(vectors) if vectors else []
    matrix = [[None] * len(texts) for _ in texts]
    embeddings = [None] * len(texts)
    for a, i in enumerate(indices):
        embeddings[i] = vectors[a]
        for b, j in enumerate(indices):
            matrix[i][j] = dense[a][b]
    retained, decisions = select_distinct(ranks, matrix, valid, threshold)
    elapsed = time.monotonic() - started
    return {
        "method": "embedding_cosine",
        "texts": texts,
        "ranks": ranks,
        "valid": valid,
        "embeddings": embeddings,
        "similarity_matrix": matrix,
        "threshold": threshold,
        "retained_ranks": retained,
        "decisions": decisions,
        "embedding_cost": {"input_tokens": tokens, "texts": len(indices), "seconds": elapsed},
        # Encoder tokens are reported separately: they are not generator-model tokens.
        "cost": {
            "input_tokens": 0,
            "output_tokens": 0,
            "forward_tokens": 0,
            "attention_pairs": 0,
            "seconds": elapsed,
        },
    }
