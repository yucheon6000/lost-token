"""Continuous vLLM V0 requests with request-local, replayable soft inputs.

Only this isolated model instance is wrapped. Installed packages are never
changed. Prefix caching and CUDA graphs are disabled for latent histories:
token IDs alone cannot identify their KV, and graphs bypass Python input hooks.
"""

from concurrent.futures import Future
from dataclasses import dataclass
import queue
import threading
import time

from .core import derived_seed, digest
from .latent import latent_choice, mix_embeddings, protected_tokens
from .recurrent_memory import StreamDecoder, StreamState, emitted_marker, reasoning_phase
from .vllm_backend import VLLMModel


class LatentProcessor:
    def __init__(self, model, exp, cfg, prompt, trace, seed, enabled):
        self.model, self.exp, self.cfg, self.trace = model, exp, cfg, trace
        self.prompt, self.seed, self.enabled = list(prompt), seed, enabled
        self.start = len(trace.ids)
        self.ids, self.pending, self.pending_records = [], [], []
        self.records = list(trace.records)
        # Rebuild completed latent inputs one decode step at a time. A long
        # prompt prefill is numerically different from the original decode.
        self.history = list(prompt)
        self.decoder = StreamDecoder(model, exp)
        self.thinking = reasoning_phase(model, self.history) == "thinking"
        self.soft = {len(prompt) + i: r for i, r in enumerate(self.records) if r["soft"]}
        self.applied = set()
        self.done = trace.terminal

    def __call__(self, output_ids, logits):
        if list(output_ids) != self.ids or self.done:
            raise RuntimeError("vLLM latent request token/termination mismatch")
        position = len(self.ids)
        state = StreamState(self.history, None, logits.float(), self.ids)
        step_seed = derived_seed(self.seed, "body", position)
        if position < self.start:
            record = self.trace.records[position]
            token = record["token"]
            if record["seed"] != step_seed:
                raise ValueError("Stored latent token seed differs during replay")
            marker = emitted_marker(self.model, self.history, token)
            self.history.append(token)
            self.ids.append(token)
            if marker:
                self.thinking = not marker.startswith("</")
            logits.fill_(-self.model.torch.inf)
            logits[token] = 0
            return logits
        guard = self.decoder.loop_guard(state)
        token, lp = self.decoder.sample(state, step_seed)
        # Apply the same repetition guard before computing the soft distribution.
        effective = logits.float()
        if guard:
            effective = effective.clone()
            effective[guard["blocked_token"]] = -self.model.torch.inf
        record = {
            "token": token,
            "seed": step_seed,
            "logprob": lp,
            **latent_choice(
                self.model,
                self.exp,
                self.cfg,
                effective,
                token,
                self.thinking,
                self.enabled,
                self.model.protected,
            ),
        }
        if record["soft"]:
            self.soft[len(self.prompt) + position] = record
        marker = emitted_marker(self.model, self.history, token)
        self.history.append(token)
        self.ids.append(token)
        self.pending.append(token)
        self.pending_records.append(record)
        self.records.append(record)
        if marker:
            self.thinking = not marker.startswith("</")
        self.done = token in self.model.eos_ids or position + 1 >= self.exp["max_output_tokens"]
        if len(self.pending) == self.cfg["checkpoint_tokens"] or self.done:
            self.trace.append(self.pending, self.pending_records, self.done)
            self.pending, self.pending_records = [], []
        logits.fill_(-self.model.torch.inf)
        logits[token] = 0
        return logits


class LatentInputHook:
    def __init__(self, runner, active):
        self.runner, self.active = runner, active
        self.selected = []
        original = runner.execute_model

        def execute(model_input, *args, **kwargs):
            selected, offset, index = [], 0, 0
            for request, seq_ids in (model_input.request_ids_to_seq_ids or {}).items():
                if len(seq_ids) != 1 or request not in active:
                    raise RuntimeError("Unknown or multi-sequence latent request")
                processor = active[request].processor
                count = model_input.query_lens[index]
                start = model_input.seq_lens[index] - count
                for position in range(start, start + count):
                    record = processor.soft.get(position)
                    if record is not None:
                        selected.append((offset + position - start, record, processor, position))
                offset += count
                index += 1
            if offset != model_input.input_tokens.numel():
                raise RuntimeError("Latent token-row mapping includes padding or missing rows")
            self.selected = selected
            try:
                return original(model_input, *args, **kwargs)
            finally:
                self.selected = []

        runner.execute_model = execute
        self.handle = runner.model.model.embed_tokens.register_forward_hook(self.embedding_hook)

    def embedding_hook(self, module, args, output):
        if not self.selected:
            return output
        import torch

        output = output.clone()
        indices = torch.tensor(
            [x[0] for x in self.selected], dtype=torch.long, device=output.device
        )
        output[indices] = mix_embeddings(torch, module.weight, [x[1] for x in self.selected])
        for _, _, processor, position in self.selected:
            processor.applied.add(position)
        return output


@dataclass
class Work:
    processor: LatentProcessor
    future: Future


class LatentEngine:
    def __init__(self, llm, model, max_batch):
        self.llm, self.model, self.max_batch = llm, model, max_batch
        self.queue, self.active = queue.Queue(), {}
        self.closed = False
        self.cancelled = threading.Event()
        self.counter = 0
        self.metrics = {"steps": 0, "requests": 0, "max_active": 0, "soft_inputs_applied": 0}
        worker = llm.llm_engine.model_executor.driver_worker
        runner = worker.worker.model_runner
        self.hook = LatentInputHook(runner, self.active)
        original = llm.llm_engine._build_logits_processors

        def processors(params, lora_request):
            params = original(params, lora_request)
            request = (params.extra_args or {}).get("latent_request")
            if request is not None:
                params.logits_processors = [self.active[request].processor]
            return params

        llm.llm_engine._build_logits_processors = processors
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def submit(self, processor):
        if self.closed:
            raise RuntimeError("Latent engine is closed")
        f = Future()
        self.queue.put(Work(processor, f))
        return f.result()

    def serve(self):
        from vllm import SamplingParams

        self.model.torch.cuda.set_device(self.model.device)
        engine = self.llm.llm_engine
        try:
            while True:
                if self.cancelled.is_set():
                    raise RuntimeError(
                        "Latent generation cancelled; durable prefixes are preserved"
                    )
                while len(self.active) < self.max_batch and not self.closed:
                    try:
                        w = self.queue.get(timeout=0.003 if not self.active else 0)
                    except queue.Empty:
                        break
                    if w is None:
                        self.closed = True
                        break
                    request = f"latent-{self.counter}"
                    self.counter += 1
                    self.active[request] = w
                    p = w.processor
                    params = SamplingParams(
                        temperature=0,
                        max_tokens=p.exp["max_output_tokens"],
                        stop_token_ids=sorted(self.model.eos_ids),
                        detokenize=False,
                        seed=0,
                        extra_args={"latent_request": request},
                    )
                    engine.add_request(request, {"prompt_token_ids": p.prompt}, params)
                    self.metrics["requests"] += 1
                self.metrics["max_active"] = max(self.metrics["max_active"], len(self.active))
                if not self.active:
                    if self.closed:
                        return
                    continue
                outputs = engine.step()
                self.metrics["steps"] += 1
                for output in outputs:
                    if not output.finished:
                        continue
                    w = self.active[output.request_id]
                    p = w.processor
                    if not p.done or p.pending:
                        raise RuntimeError("Latent engine stopped without a durable terminal block")
                    expected = {i for i in p.soft if i < len(p.history) - 1}
                    if p.applied != expected:
                        raise RuntimeError(
                            "A latent input was missed, reused or applied to another request"
                        )
                    actual = list(output.outputs[0].token_ids)
                    if actual != p.ids and not (
                        p.ids and p.ids[-1] in self.model.eos_ids and actual == p.ids[:-1]
                    ):
                        raise RuntimeError("Engine output differs from latent token ledger")
                    self.metrics["soft_inputs_applied"] += len(p.applied)
                    self.active.pop(output.request_id)
                    w.future.set_result(p)
        except BaseException as exc:
            for request, work in self.active.items():
                try:
                    engine.abort_request(request)
                except Exception:
                    pass
                if not work.future.done():
                    work.future.set_exception(exc)
            while not self.queue.empty():
                work = self.queue.get()
                if work is not None:
                    work.future.set_exception(exc)
            self.closed = True

    def close(self):
        self.queue.put(None)
        self.thread.join()

    def cancel(self):
        self.cancelled.set()


class LatentModel(VLLMModel):
    def __init__(self, cfg, log=print):
        if not cfg.get("vllm_enforce_eager") or cfg.get("vllm_prefix_caching", True):
            raise ValueError(
                "Latent KV requires eager execution and disabled token-only prefix cache"
            )
        super().__init__(cfg, log)
        llm = self.engine.llm
        self.engine.close()
        self.protected = protected_tokens(self)
        self.engine = LatentEngine(llm, self, cfg.get("vllm_batch_size", 8))
