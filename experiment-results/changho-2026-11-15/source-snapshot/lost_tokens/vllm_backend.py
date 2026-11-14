"""Batched vLLM V0 decoding with protocol-controlled per-position sampling.

The pinned single-process executor invokes a request-local logits processor in
the engine process. It observes raw logits, samples with the original token seed,
and stops *before* a qualifying fork. No speculative body tokens are committed.
Prefix caching owns physical KV storage; protocol states own independent IDs.
"""

from concurrent.futures import Future
from dataclasses import dataclass
import os
import queue
import threading
import time

from .backend import LocalModel
from .core import derived_seed, digest
from .recurrent_memory import (
    StreamDecoder,
    StreamState,
    distribution_entropy,
    emitted_marker,
    fragment_text,
)


class ProtocolProcessor:
    """One processor per request. vLLM's own sampler only executes our choice."""

    def __init__(self, model, exp, root, count, seed, body_position=0, scan=False, first=None):
        self.model, self.exp, self.root = model, exp, root
        self.count, self.seed, self.body_position = count, seed, body_position
        self.scan, self.first = scan, first
        self.ids, self.logprobs, self.entropies = [], [], []
        self.checks, self.guards = [], []
        self.fork, self.marker, self.done = None, None, False
        # These helpers use the same raw probabilities, top-k/top-p and guard as HF.
        self.decoder = StreamDecoder(model, exp)

    def __call__(self, output_ids, logits):
        torch = self.model.torch
        if list(output_ids) != self.ids:
            raise RuntimeError("vLLM output diverged from the protocol-controlled tokens")
        forced_stop = min(self.model.eos_ids)
        if self.done or len(self.ids) == self.count:
            self.done = True
            logits.fill_(-torch.inf)
            logits[forced_stop] = 0
            return logits
        state = StreamState(
            self.root.ids + self.ids, None, logits.float(), self.root.generated_ids + self.ids
        )
        offset = len(self.ids)
        if self.scan:
            dist = self.decoder.candidates(state)
            self.checks.append({"body_position": self.body_position + offset, **dist})
            if dist["eligible"]:
                self.fork, self.done = dist, True
                logits.fill_(-torch.inf)
                logits[forced_stop] = 0
                return logits
        self.entropies.append(distribution_entropy(state.logits))
        if offset == 0 and self.first is not None:
            token = self.first
            lp = float(state.logits.log_softmax(-1)[token])
        else:
            guard = self.decoder.loop_guard(state)
            seed = (
                derived_seed(self.seed, "rollout", offset)
                if self.first is not None
                else derived_seed(self.seed, "body", self.body_position + offset)
            )
            token, lp = self.decoder.sample(state, seed)
            if guard:
                self.guards.append({"offset": offset, "sampled_token": token, **guard})
        marker = emitted_marker(self.model, state.ids, token)
        self.ids.append(token)
        self.logprobs.append(lp)
        self.marker = marker
        self.done = token in self.model.eos_ids or bool(
            marker and (self.first is None or marker.startswith("</"))
        )
        logits.fill_(-torch.inf)
        logits[token] = 0
        return logits


@dataclass
class Pending:
    processor: ProtocolProcessor
    future: Future


class BatchEngine:
    """A single owner batches decoder requests from concurrent case threads."""

    def __init__(self, llm, model, max_batch, wait_ms=3):
        self.llm, self.model, self.max_batch = llm, model, max_batch
        self.wait_seconds = wait_ms / 1000
        self.queue = queue.Queue()
        self.closed = False
        self.processors = {}
        self.metrics = {"batches": 0, "requests": 0, "max_batch": 0, "body_and_rollout_tokens": 0}
        # v0.10.2 rejects user processors at add_request even in V0's single-step
        # engine. Its internal processor builder remains the execution
        # point for guided decoding. Attach our request hook there, after input
        # validation, without modifying the installed vLLM package.
        original_builder = llm.llm_engine._build_logits_processors

        def build_processors(params, lora_request):
            params = original_builder(params, lora_request)
            key = (params.extra_args or {}).get("lost_tokens_processor")
            if key is not None:
                params.logits_processors = [self.processors[key]]
            return params

        llm.llm_engine._build_logits_processors = build_processors
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def submit(self, processor):
        if self.closed:
            raise RuntimeError("vLLM batch engine is closed")
        future = Future()
        self.queue.put(Pending(processor, future))
        return future.result()

    def _serve(self):
        from vllm import SamplingParams

        self.model.torch.cuda.set_device(self.model.device)
        while True:
            first = self.queue.get()
            if first is None:
                return
            batch = [first]
            deadline = time.monotonic() + self.wait_seconds
            while len(batch) < self.max_batch:
                try:
                    batch.append(self.queue.get(timeout=max(0, deadline - time.monotonic())))
                except queue.Empty:
                    break
            try:
                processors = [item.processor for item in batch]
                self.processors = {id(p): p for p in processors}
                params = [
                    SamplingParams(
                        temperature=0,
                        max_tokens=p.count + 1,
                        stop_token_ids=sorted(self.model.eos_ids),
                        extra_args={"lost_tokens_processor": id(p)},
                        detokenize=False,
                        seed=0,
                    )
                    for p in processors
                ]
                outputs = self.llm.generate(
                    [{"prompt_token_ids": p.root.ids} for p in processors],
                    params,
                    use_tqdm=False,
                )
                if len(outputs) != len(batch):
                    raise RuntimeError("vLLM returned an incomplete batch")
                for p, output in zip(processors, outputs):
                    if not p.ids and p.fork is None:
                        raise RuntimeError("Protocol logits processor was not invoked locally")
                    actual = list(output.outputs[0].token_ids)
                    expected = list(p.ids)
                    # A final EOS may be omitted by the pinned engine's stop logic.
                    if expected and expected[-1] in self.model.eos_ids and actual == expected[:-1]:
                        continue
                    if actual[: len(expected)] != expected:
                        raise RuntimeError("Engine tokens do not match protocol ledger")
                    if actual[len(expected) :] not in ([], [min(self.model.eos_ids)]):
                        raise RuntimeError("Unexpected extra tokens after protocol stop")
                for item in batch:
                    item.future.set_result(item.processor)
                self.metrics["batches"] += 1
                self.metrics["requests"] += len(batch)
                self.metrics["max_batch"] = max(self.metrics["max_batch"], len(batch))
                self.metrics["body_and_rollout_tokens"] += sum(len(p.ids) for p in processors)
                self.processors = {}
            except BaseException as exc:
                for item in batch:
                    item.future.set_exception(exc)

    def close(self):
        self.closed = True
        self.queue.put(None)
        self.thread.join()


class VLLMModel(LocalModel):
    def __init__(self, cfg, log=print):
        # V0 UniProcExecutor is required for the request-local raw-logit hook.
        # A separate backend identity prevents mixing these checkpoints with HF.
        os.environ["VLLM_USE_V1"] = "0"
        # Keep callbacks on the engine's inference-mode thread. vLLM's optional
        # processor thread pool does not propagate PyTorch inference mode.
        os.environ.pop("VLLM_LOGITS_PROCESSOR_THREADS", None)
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer, GenerationConfig
        from vllm import LLM, __version__

        if __version__ != "0.10.2":
            raise RuntimeError("This protocol hook requires the pinned vLLM 0.10.2")

        self.cfg, self.log, self.torch = cfg, log, torch
        self.device = torch.device(cfg["device"])
        if self.device.type != "cuda" or self.device.index not in (None, 0):
            raise ValueError(
                "vLLM uses one visible GPU per worker; select with CUDA_VISIBLE_DEVICES"
            )
        torch.set_num_threads(cfg["threads"])
        torch.cuda.set_device(self.device)
        torch.backends.cuda.matmul.allow_tf32 = False
        path = snapshot_download(
            cfg["name"],
            revision=cfg["revision"],
            cache_dir=cfg["cache_dir"],
            local_files_only=cfg["local_files_only"],
        )
        self.tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=False)
        eos = GenerationConfig.from_pretrained(path).eos_token_id
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])
        self.special_ids = set(self.tokenizer.all_special_ids)
        self.parameter_count = None
        batch_size = cfg.get("vllm_batch_size", 8)
        llm = LLM(
            model=path,
            dtype=cfg["dtype"],
            tensor_parallel_size=1,
            max_model_len=cfg["max_context_tokens"],
            gpu_memory_utilization=cfg["gpu_memory_fraction"],
            enable_prefix_caching=True,
            enable_chunked_prefill=True,
            max_num_seqs=batch_size,
            max_num_batched_tokens=cfg.get("vllm_batch_tokens", 4096),
            enforce_eager=cfg.get("vllm_enforce_eager", False),
            disable_async_output_proc=True,
            seed=0,
        )
        self.engine = BatchEngine(llm, self, batch_size)

    def close(self):
        self.engine.close()

    def resources(self):
        return {
            **super().resources(),
            "backend": "vllm-v0-0.10.2",
            "batch_engine": dict(self.engine.metrics),
        }


class VLLMStreamDecoder(StreamDecoder):
    def prefill(self, ids):
        self.model._check(ids)
        # KV is materialized lazily at the next batched engine request.
        return StreamState(list(ids), None, None)

    def advance(self, state, ids, block_size=1, generated=False):
        self.model._check(state.ids, len(ids))
        state.ids.extend(ids)
        if generated:
            state.generated_ids.extend(ids)
        return state

    def segment(self, state, count, seed, body_position, scan):
        start = time.monotonic()
        root_length = len(state.ids)
        p = self.model.engine.submit(
            ProtocolProcessor(self.model, self.exp, state, count, seed, body_position, scan)
        )
        self.advance(state, p.ids, generated=True)
        return {
            "ids": p.ids,
            "raw_log_probabilities": p.logprobs,
            "checks": p.checks,
            "fork": p.fork,
            "stop_marker": p.marker,
            "guard_events": p.guards,
            "cost": self.cost(root_length, len(p.ids), len(p.ids), time.monotonic() - start),
        }

    def rollout(self, root, first, seed, count=None):
        start = time.monotonic()
        count = self.exp["branch_tokens"] if count is None else count
        if not 1 <= count <= self.exp["branch_tokens"]:
            raise ValueError("Invalid rollout length")
        origin = digest(root.ids)
        p = self.model.engine.submit(
            ProtocolProcessor(self.model, self.exp, root, count, seed, first=first)
        )
        return {
            "ids": p.ids,
            "text": fragment_text(self.model, p.ids),
            "first_token": first,
            "seed": seed,
            "stop_marker": p.marker,
            "guard_events": p.guards,
            "origin_sha256": origin,
            "raw_log_probabilities": p.logprobs,
            "entropies": p.entropies,
            "cost": self.cost(len(root.ids), len(p.ids), len(p.ids), time.monotonic() - start),
        }


def install():
    from . import recurrent_memory

    recurrent_memory.StreamDecoder = VLLMStreamDecoder
