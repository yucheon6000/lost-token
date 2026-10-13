#!/usr/bin/env python3
"""Compare token trajectories before enabling CPU optimizations on a real GPU."""

import argparse
import copy
import gc
from pathlib import Path
import time

from lost_tokens.backend import LocalModel
from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.core import atomic_json, digest, source_fingerprint
from lost_tokens.recurrent_memory import StreamDecoder
from lost_tokens.runtime import environment


def verify(spec, device, tokens=128, prefixes=(0, 2048, 8192, 32768), log=print):
    import torch

    if not device.startswith("cuda:") or not torch.cuda.is_available():
        raise RuntimeError("Real GPU parity verification requires an available CUDA device")
    spec = copy.deepcopy(spec)
    spec["model"]["device"] = device
    spec["model"]["exact_cpu_optimizations"] = False
    spec["model"]["exact_stateless_graphs"] = True
    model = LocalModel(spec["model"], log)
    warm_decoder = StreamDecoder(model, spec["experiment"])
    warm_state = warm_decoder.prefill(model.prompt("Compute 7 times 13."))
    warm_decoder.segment(warm_state, 2, 95021, 0, False)
    del warm_state, warm_decoder
    model._sync()
    results = []
    for prefix_tokens in prefixes:
        prompt = model.prompt("Compute 7 times 13. Explain your reasoning.")
        prompt += (model.encode(" Let us examine this carefully.") * (prefix_tokens + 1))[
            :prefix_tokens
        ]
        outputs = []
        for enabled in (False, True):
            model.cfg["exact_cpu_optimizations"] = enabled
            for handle in model.exact_graphs:
                handle.enabled = enabled
                handle.forward.__self__.forward = handle if enabled else handle.forward
            decoder = StreamDecoder(model, spec["experiment"])
            started = time.monotonic()
            state = decoder.prefill(prompt)
            segment = decoder.segment(state, tokens, 95021, 0, False)
            body = list(segment["ids"])
            # Exercise independent candidate caches and sentence-based rollouts.
            lp = state.logits.log_softmax(-1)
            candidates = [
                t for t in lp.argsort(descending=True).tolist() if t not in model.special_ids
            ][:2]
            previews = [
                decoder.rollout(state, token, 900 + i, tokens) for i, token in enumerate(candidates)
            ]
            decoder.advance(state, [decoder.think_end], generated=True)
            decoder.final_answer_only = True
            final = decoder.segment(state, tokens, 95021, len(body) + 1, False)
            model._sync()
            outputs.append(
                {
                    "ids": body,
                    "logprobs": segment["raw_log_probabilities"],
                    "previews": [
                        {
                            k: p[k]
                            for k in (
                                "ids",
                                "raw_log_probabilities",
                                "stop_marker",
                                "sentence_ends",
                            )
                        }
                        for p in previews
                    ],
                    "final_ids": final["ids"],
                    "final_logprobs": final["raw_log_probabilities"],
                    "seconds": time.monotonic() - started,
                }
            )
        timings = [o.pop("seconds") for o in outputs]
        if outputs[0] != outputs[1]:
            raise AssertionError(
                f"Token/logprob/rollout parity failed at prefix length {prefix_tokens}"
            )
        results.append(
            {
                "prefix_tokens": prefix_tokens,
                "trajectory_sha256": digest(outputs[0]),
                "seconds_original": timings[0],
                "seconds_optimized": timings[1],
            }
        )
        log(
            f"GPU parity passed: prefix={prefix_tokens}; original={timings[0]:.2f}s optimized={timings[1]:.2f}s",
            flush=True,
        )
    result = {
        "passed": True,
        "device": device,
        "source": source_fingerprint(),
        "environment": environment(),
        "checks": results,
        "graph_blocks": len(model.exact_graphs),
        "graph_replays": sum(h.replays for h in model.exact_graphs),
    }
    del state, decoder, model
    gc.collect()
    torch.cuda.empty_cache()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/sparse-sentence-rollouts.json")
    )
    parser.add_argument("--work-dir", type=Path, default=Path("workspace"))
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--tokens", type=int, default=128)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.tokens < 1:
        parser.error("--tokens must be positive")
    spec = runtime_spec(load_spec(args.config), args.work_dir, args.model_cache)
    result = verify(spec, args.device, args.tokens)
    atomic_json(args.output or args.work_dir / "outputs" / "gpu-exact-parity.json", result)


if __name__ == "__main__":
    main()
