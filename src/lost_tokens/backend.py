"""Local frozen causal LM. Sampling, token branching and scoring share one model."""

from __future__ import annotations

import time


class LocalModel:
    def __init__(self, config: dict, log=print):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.cfg = config
        self.log = log
        self.device = torch.device(config["device"])
        torch.set_num_threads(config["threads"])
        if self.device.type == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA requested but unavailable; choose CPU explicitly if desired"
                )
            torch.cuda.set_per_process_memory_fraction(config["gpu_memory_fraction"], self.device)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.cuda.reset_peak_memory_stats(self.device)
        kwargs = {
            "revision": config["revision"],
            "cache_dir": config["cache_dir"],
            "local_files_only": config["local_files_only"],
            "trust_remote_code": False,
            "token": False,
        }
        self.tokenizer = AutoTokenizer.from_pretrained(config["name"], **kwargs)
        self.model = (
            AutoModelForCausalLM.from_pretrained(
                config["name"],
                dtype=getattr(torch, config["dtype"]),
                attn_implementation="sdpa",
                **kwargs,
            )
            .to(self.device)
            .eval()
        )
        self.model.requires_grad_(False)
        eos = self.model.generation_config.eos_token_id
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])
        self.special_ids = set(self.tokenizer.all_special_ids)
        self.parameter_count = sum(p.numel() for p in self.model.parameters())

    def encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, ids: list[int]) -> str:
        return self.tokenizer.decode(ids, skip_special_tokens=True)

    def prompt(self, text: str) -> list[int]:
        return self.tokenizer.apply_chat_template(
            [{"role": "user", "content": text}],
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=self.cfg["enable_thinking"],
        )

    def _check(self, ids: list[int], extra: int = 0) -> None:
        if not ids:
            raise ValueError("Empty model input")
        if len(ids) + extra > self.cfg["max_context_tokens"]:
            raise ValueError("Context budget exceeded; refusing silent truncation")

    def _sync(self):
        if self.device.type == "cuda":
            self.torch.cuda.synchronize(self.device)

    @staticmethod
    def _cost(n: int, steps: int, output: int, elapsed: float) -> dict:
        # Counts logical causal attention pairs, not measured FLOPs or GPU kernel work.
        extra = max(0, steps - 1)
        return {
            "input_tokens": n,
            "output_tokens": output,
            "forward_tokens": n + extra,
            "attention_pairs": n * (n + 1) // 2 + extra * n + extra * (extra + 1) // 2,
            "seconds": elapsed,
        }

    def candidates(self, ids: list[int], count: int) -> dict:
        self._check(ids)
        torch = self.torch
        self._sync()
        start = time.monotonic()
        with torch.inference_mode():
            logits = (
                self.model(
                    input_ids=torch.tensor([ids], device=self.device),
                    use_cache=False,
                    logits_to_keep=1,
                )
                .logits[0, -1]
                .float()
            )
            lp = torch.log_softmax(logits, -1)
            values, indices = torch.topk(lp, count)
            entropy = -(lp.exp() * lp).sum().item()
            items = [
                {
                    "token_id": int(i),
                    "text": self.decode([int(i)]),
                    "rank": rank + 1,
                    "log_probability": float(v),
                    "probability": float(v.exp()),
                    "special": int(i) in self.special_ids,
                }
                for rank, (i, v) in enumerate(zip(indices, values))
            ]
        self._sync()
        return {
            "items": items,
            "entropy": entropy,
            "cost": self._cost(len(ids), 1, 0, time.monotonic() - start),
        }

    def generate(
        self, ids: list[int], max_tokens: int, seed: int, temperature: float, top_p: float
    ) -> dict:
        self._check(ids, max_tokens)
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        torch = self.torch
        generator = torch.Generator(device=self.device).manual_seed(seed)
        token_input = torch.tensor([ids], device=self.device)
        cache = None
        generated = []
        self._sync()
        start = time.monotonic()
        last_log = start
        with torch.inference_mode():
            for _ in range(max_tokens):
                out = self.model(
                    input_ids=token_input, past_key_values=cache, use_cache=True, logits_to_keep=1
                )
                cache = out.past_key_values
                logits = out.logits[0, -1].float() / temperature
                sorted_logits, indices = torch.sort(logits, descending=True)
                probabilities = torch.softmax(sorted_logits, -1)
                # Keep the token crossing the threshold, including the first token.
                mask = probabilities.cumsum(-1) - probabilities > top_p
                probabilities.masked_fill_(mask, 0)
                position = torch.multinomial(probabilities, 1, generator=generator)
                token = int(indices[position].item())
                generated.append(token)
                if token in self.eos_ids:
                    break
                token_input = torch.tensor([[token]], device=self.device)
                elapsed = time.monotonic() - start
                if time.monotonic() - last_log >= 15:
                    eta = elapsed / len(generated) * (max_tokens - len(generated))
                    self.log(
                        f"generation {len(generated)}/{max_tokens} tokens; "
                        f"elapsed={elapsed:.1f}s ETA(cap)={eta:.1f}s"
                    )
                    last_log = time.monotonic()
        self._sync()
        elapsed = time.monotonic() - start
        return {
            "ids": generated,
            "text": self.decode(generated),
            "seed": seed,
            "ended": generated[-1] in self.eos_ids,
            "cost": self._cost(len(ids), len(generated), len(generated), elapsed),
        }

    def score(self, ids: list[int], target: str) -> dict:
        """Offline teacher-forced log score. Gold never enters generation or selection."""
        target_ids = self.encode(target)
        if not target_ids:
            raise ValueError("Empty scoring target")
        self._check(ids, len(target_ids))
        torch = self.torch
        token_input = torch.tensor([ids], device=self.device)
        cache = None
        values = []
        self._sync()
        start = time.monotonic()
        with torch.inference_mode():
            for token in target_ids:
                out = self.model(
                    input_ids=token_input, past_key_values=cache, use_cache=True, logits_to_keep=1
                )
                cache = out.past_key_values
                lp = torch.log_softmax(out.logits[0, -1].float(), -1)
                values.append(float(lp[token].item()))
                token_input = torch.tensor([[token]], device=self.device)
        self._sync()
        return {
            "log_probability": sum(values),
            "target_tokens": len(target_ids),
            "cost": self._cost(len(ids), len(target_ids), 0, time.monotonic() - start),
        }

    def resources(self) -> dict:
        rss_mib = 0.0
        try:
            import resource
            rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except ImportError:
            try:
                import psutil
                rss_mib = psutil.Process().memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        result = {
            "peak_rss_mib": rss_mib,
            "parameters": self.parameter_count,
            "device": str(self.device),
        }
        if self.device.type == "cuda":
            result.update(
                peak_cuda_allocated_mib=self.torch.cuda.max_memory_allocated(self.device) / 2**20,
                peak_cuda_reserved_mib=self.torch.cuda.max_memory_reserved(self.device) / 2**20,
            )
        return result
