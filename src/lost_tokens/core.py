"""Atomic, content-addressed inference checkpoints and shared utilities."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def extract_choice(text: str, choices: list[str]) -> str | None:
    """Accept an explicitly marked option; do not infer it from scratch reasoning."""
    matches = list(
        re.finditer(r"Final answer\s*:\s*(?:\*\*)?\s*\(?([A-Z])\)?(?![A-Za-z0-9])", text, re.I)
    )
    if not matches:
        return None
    value = matches[-1].group(1).upper()
    return value if value in choices else None


class RunStore:
    """A checkpoint per completed model call, keyed by its full request and seed.

    Sampling uses a fresh per-call generator. Replaying an unfinished call from its
    saved request restores its complete RNG state without touching finished calls.
    No optimizer, training scheduler, sampler cursor or distributed state exists.
    """

    def __init__(self, path: Path, identity: dict, resume: bool = False):
        self.path = path
        self.identity = identity
        if resume:
            saved = json.loads((path / "identity.json").read_text(encoding="utf-8"))
            if saved != identity:
                raise ValueError("Resume rejected: config, data, code or runtime identity changed")
        else:
            path.mkdir(parents=True, exist_ok=False)
            atomic_json(path / "identity.json", identity)
        self.hits = 0
        self.calls = 0
        self.status("resumed" if resume else "started")

    def status(self, state: str, **details) -> None:
        atomic_json(self.path / "status.json", {"state": state, "at": now(), **details})

    def call(self, label: str, request: dict, function):
        key = digest({"label": label, "request": request})
        path = self.path / "checkpoints" / f"{key}.json"
        if path.exists():
            item = json.loads(path.read_text(encoding="utf-8"))
            if item.get("sha256") != digest(item.get("payload")):
                raise ValueError(f"Corrupt checkpoint: {path}")
            payload = item["payload"]
            if payload["request"] != request or payload["label"] != label:
                raise ValueError(f"Checkpoint identity mismatch: {path}")
            self.hits += 1
            return payload["result"]
        result = function()
        payload = {"label": label, "request": request, "result": result, "completed_at": now()}
        atomic_json(path, {"payload": payload, "sha256": digest(payload)})
        self.calls += 1
        return result


def derived_seed(seed: int, *parts) -> int:
    return int(digest([seed, *parts])[:8], 16) % (2**31)


def sum_cost(*results: dict) -> dict:
    keys = ("input_tokens", "output_tokens", "forward_tokens", "attention_pairs", "seconds")
    return {key: sum(r.get("cost", {}).get(key, 0) for r in results) for key in keys}


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def source_files():
    package = Path(__file__).resolve().parent
    return {
        "lost_tokens/" + str(p.relative_to(package)): p
        for p in sorted(package.rglob("*"))
        if p.suffix in (".py", ".json") and "__pycache__" not in p.parts
    }


def source_fingerprint(root=None):
    return {name: file_digest(path) for name, path in source_files().items()}
