"""Exact-dtype parent KV offload for independent long-context candidate rollouts.

The parent temporarily resides on CPU. The original v4 rollout deep-copies it,
and advance moves that independent candidate to GPU before the first forward.
The parent is restored after the candidate is freed. No KV quantization, prefix
sharing, token pruning, or model/sampling changes are introduced.
"""

import time

from lost_tokens.recurrent_memory import StreamDecoder


def move_cache(cache, device, torch):
    from transformers.cache_utils import DynamicCache, DynamicLayer

    if not isinstance(cache, DynamicCache) or cache.offloading:
        raise TypeError("Only the pinned non-offloaded DynamicCache is supported")
    with torch.inference_mode():
        for layer in cache.layers:
            if type(layer) is not DynamicLayer:
                raise TypeError("Only full-attention DynamicLayer is supported")
            if layer.is_initialized:
                layer.keys = layer.keys.to(device)
                layer.values = layer.values.to(device)
                layer.device = torch.device(device)


class LongContextDecoder(StreamDecoder):
    def advance(self, state, ids, block_size=1, generated=False):
        if state.cache is not None and state.cache.layers:
            layer = state.cache.layers[0]
            if layer.is_initialized and layer.keys.device != self.model.device:
                move_cache(state.cache, self.model.device, self.torch)
        return super().advance(state, ids, block_size=block_size, generated=generated)

    def rollout(self, root, first, seed, count=None):
        threshold = self.model.cfg["rollout_cache_offload_threshold_tokens"]
        if self.model.device.type != "cuda" or len(root.ids) <= threshold:
            return super().rollout(root, first, seed, count)
        started = time.monotonic()
        try:
            move_cache(root.cache, "cpu", self.torch)
            result = super().rollout(root, first, seed, count)
        finally:
            move_cache(root.cache, self.model.device, self.torch)
        self.model._sync()
        result["cost"]["seconds"] = time.monotonic() - started
        return result


def install():
    """Explicit opt-in adapter; original v4 source and completed runs stay frozen."""
    import lost_tokens.recurrent_memory as memory

    memory.StreamDecoder = LongContextDecoder
