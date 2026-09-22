"""Process-local runtime metadata and interruption handling."""

import contextlib
import importlib.metadata
import platform
import signal
import threading
import time


def install_interrupt_handlers():
    """A launcher and its process group may deliver the same signal twice.

    Stop accepting interrupts before checkpoint/status cleanup so a forwarded
    second SIGTERM cannot interrupt the first signal's recovery bookkeeping.
    """
    received = False

    def interrupt(signum, frame):
        nonlocal received
        if received:
            return
        received = True
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal.SIG_IGN)
        raise KeyboardInterrupt(f"signal {signum}")

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupt)
    return interrupt


@contextlib.contextmanager
def heartbeat(message, log):
    finished = threading.Event()
    start = time.monotonic()

    def update():
        while not finished.wait(20):
            log(f"{message}; elapsed={time.monotonic() - start:.0f}s; ETA not yet available")

    thread = threading.Thread(target=update, daemon=True)
    thread.start()
    log(message)
    try:
        yield
    finally:
        finished.set()
        thread.join()


def environment():
    import torch

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("torch", "transformers", "huggingface-hub", "tokenizers", "numpy")
        },
        "cuda_runtime": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
