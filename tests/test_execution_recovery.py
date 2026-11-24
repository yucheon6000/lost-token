from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import time
import unittest

from lost_tokens.config import load_spec, runtime_spec
from lost_tokens.runner import checkpoint_age
from lost_tokens.vllm_backend import initialization_lock


class ExecutionRecoveryTests(unittest.TestCase):
    def test_old_heartbeat_does_not_immediately_fail_a_resumed_worker(self):
        self.assertEqual(checkpoint_age({"epoch": 10}, 1000, 1001), 1)
        self.assertEqual(checkpoint_age({"epoch": 1010}, 1000, 1012), 2)
        self.assertEqual(checkpoint_age({}, 1000, 1901), 901)
        self.assertEqual(checkpoint_age({"epoch": 1100}, 1000, 1090), 0)

    def test_parallel_initializations_cannot_choose_ports_at_the_same_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locks/init.lock"
            counter_lock = threading.Lock()
            ready = threading.Barrier(3)
            active = peak = 0

            def initialize(_):
                nonlocal active, peak
                ready.wait()
                with initialization_lock(path):
                    with counter_lock:
                        active += 1
                        peak = max(peak, active)
                    time.sleep(0.02)
                    with counter_lock:
                        active -= 1

            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(initialize, range(3)))
            self.assertEqual(peak, 1)

    def test_coordination_path_comes_from_explicit_work_storage(self):
        cfg = load_spec(Path(__file__).resolve().parents[1] / "configs/vllm-argmax.json")
        with tempfile.TemporaryDirectory() as directory:
            result = runtime_spec(cfg, directory)
            self.assertEqual(
                Path(result["model"]["initialization_lock"]),
                Path(directory) / "locks/vllm-initialization.lock",
            )
            self.assertNotIn("initialization_lock", cfg["model"])
