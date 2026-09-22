from pathlib import Path
import unittest
import torch
from transformers import Qwen3Config, Qwen3ForCausalLM
from lost_tokens.backend import LocalModel

Path("temp/diagnostics").mkdir(parents=True, exist_ok=True)


class AsciiTokenizer:
    def encode(self, text, add_special_tokens=False):
        return [ord(c) for c in text]

    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i) for i in ids if i != 127)


class OnlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(91)
        model = LocalModel.__new__(LocalModel)
        model.torch, model.device = torch, torch.device("cpu")
        model.cfg = {"max_context_tokens": 4096}
        model.log = lambda message: None
        model.tokenizer = AsciiTokenizer()
        model.prompt = model.encode
        model.eos_ids, model.special_ids = {127}, {127}
        config = Qwen3Config(
            vocab_size=128,
            hidden_size=16,
            intermediate_size=32,
            num_hidden_layers=2,
            num_attention_heads=2,
            num_key_value_heads=1,
            head_dim=8,
            max_position_embeddings=4096,
        )
        model.model = Qwen3ForCausalLM(config).eval().requires_grad_(False)
        model.parameter_count = sum(p.numel() for p in model.model.parameters())
        cls.model = model
