"""Local frozen causal LM. Tokenization, chat prompt and the raw forward model.

All decoding (scanning, sampling, candidate rollouts) lives in StreamDecoder.
"""

from __future__ import annotations


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

    def resources(self) -> dict:
        import resource

        result = {
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "parameters": self.parameter_count,
            "device": str(self.device),
        }
        if self.device.type == "cuda":
            result.update(
                peak_cuda_allocated_mib=self.torch.cuda.max_memory_allocated(self.device) / 2**20,
                peak_cuda_reserved_mib=self.torch.cuda.max_memory_reserved(self.device) / 2**20,
            )
        return result
