"""Static replay retains eager fallbacks and requires the validated architecture."""

from types import SimpleNamespace
import unittest

import torch

from lost_tokens.exact_graphs import StatelessGraph, install
from lost_tokens.config import load_spec, validate_spec


class ExactGraphTests(unittest.TestCase):
    def test_cpu_inference_and_multitoken_fallback_preserve_values(self):
        module = torch.nn.Linear(16, 8).eval().requires_grad_(False)
        graph = StatelessGraph(module, torch)
        for shape in ((1, 1, 16), (1, 4, 16), (2, 1, 16)):
            x = torch.randn(*shape)
            with torch.inference_mode():
                self.assertTrue(torch.equal(graph(x), module(x)))
        self.assertIsNone(graph.graph)
        self.assertEqual(graph.replays, 0)

    def test_install_rejects_unallocated_cpu_model(self):
        model = SimpleNamespace(device=torch.device("cpu"))
        with self.assertRaisesRegex(ValueError, "CUDA"):
            install(model)

    def test_graph_flag_requires_boolean(self):
        for value in (1, "true", None):
            spec = load_spec()
            spec["model"]["exact_stateless_graphs"] = value
            with self.assertRaisesRegex(ValueError, "boolean"):
                validate_spec(spec)
