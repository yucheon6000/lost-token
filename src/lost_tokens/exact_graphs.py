"""Replay unchanged Qwen3 MLP/RMSNorm kernels for single-token inference.

Attention, KV shapes, multi-token forwards and sampling remain eager. Each
module owns its graph buffers; branches own independent KV caches as before.
"""


def signature(tensor):
    return tensor.shape, tensor.dtype, tensor.device, tensor.stride()


class StatelessGraph:
    def __init__(self, module, torch):
        self.forward, self.torch = module.forward, torch
        self.graph = None
        self.enabled = True
        self.replays = 0

    def __call__(self, x):
        torch = self.torch
        if (
            not self.enabled
            or not torch.is_inference_mode_enabled()
            or x.shape[:2] != (1, 1)
            or x.device.type != "cuda"
        ):
            return self.forward(x)
        if self.graph is None:
            self.input = x.clone()
            stream = torch.cuda.Stream(device=x.device)
            stream.wait_stream(torch.cuda.current_stream(x.device))
            with torch.cuda.stream(stream):
                for _ in range(3):
                    self.forward(self.input)
            torch.cuda.current_stream(x.device).wait_stream(stream)
            self.graph = torch.cuda.CUDAGraph()
            with torch.cuda.graph(self.graph, stream=stream):
                self.output = self.forward(self.input)
        if signature(x) != signature(self.input):
            return self.forward(x)
        self.input.copy_(x)
        with torch.cuda.device(x.device):
            self.graph.replay()
        self.replays += 1
        return self.output


def install(model):
    import transformers

    if (
        model.device.type != "cuda"
        or transformers.__version__ != "4.57.1"
        or model.model.config.model_type != "qwen3"
    ):
        raise ValueError("Exact stateless graphs require CUDA and pinned Qwen3/Transformers 4.57.1")
    handles = []
    for module in model.model.modules():
        if type(module).__name__ in ("Qwen3MLP", "Qwen3RMSNorm"):
            handle = StatelessGraph(module, model.torch)
            module.forward = handle
            handles.append(handle)
    if not handles:
        raise ValueError("No supported stateless blocks found")
    model.exact_graphs = handles
    return handles
