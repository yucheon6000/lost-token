"""Immutable, portable AR outcomes reused for successive ours-only studies."""

import copy
from datetime import datetime
import json
from pathlib import Path

from .core import atomic_json, digest, file_digest
from .reporting import collect, summarize_vs_baseline


def conditions(study):
    spec = study["spec"]
    model = {
        k: v
        for k, v in spec["model"].items()
        if k not in ("cache_dir", "device", "vllm_batch_size")
    }
    return {
        "cohort_version": study["cohort_version"],
        "cohort_manifest_sha256": study["cohort_manifest_sha256"],
        "hardware_profile": study.get("hardware_profile"),
        "model": model,
        "data": spec["data"],
        "decoding": {
            k: spec["experiment"].get(k)
            for k in (
                "seed",
                "temperature",
                "top_k",
                "top_p",
                "max_output_tokens",
                "checkpoint_body_tokens",
                "prefill_chunk_tokens",
                "repetition_guard",
                "budget_forcing",
            )
        },
        "batches": {
            task: cfg["model"].get("vllm_batch_size", 8)
            for task, cfg in study.get("task_specs", {}).items()
        },
        "scoring_and_seed_sources": {
            k: study["source"].get(k)
            for k in ("lost_tokens/core.py", "lost_tokens/math_scoring.py", "lost_tokens/data.py")
        },
        "runtime": study.get("environment", {}).get("runtime"),
        "scoring_packages": study.get("environment", {}).get("scoring_packages"),
    }


def read_reference(path, expected=None):
    wrapper = json.loads(Path(path).read_text())
    payload = wrapper["payload"]
    if wrapper["sha256"] != digest(payload):
        raise ValueError("Frozen baseline content hash changed")
    if expected is not None:
        actual = copy.deepcopy(payload["conditions"])
        actual["batches"] = {k: actual["batches"].get(k) for k in expected["batches"]}
        if actual != expected:
            raise ValueError(
                "Frozen baseline comparison conditions differ; use a new baseline family"
            )
    for task, n in payload["counts"].items():
        rows = payload["outcomes"][task]
        if len(rows) != n or len({r["id"] for r in rows}) != n:
            raise ValueError("Frozen baseline must contain every required ID exactly once")
        if any(r["task"] != task for r in rows):
            raise ValueError("Frozen baseline task mismatch")
    return wrapper


def freeze(study, work, destination):
    """Return None until all baseline tasks are complete and audited; never overwrite."""
    outcomes, evidence = {}, {}
    for task, name in study["runs"].items():
        run = Path(work) / "outputs" / name
        status = run / "status.json"
        if (
            not status.exists()
            or not (run / "plan.json").exists()
            or not json.loads(status.read_text()).get("audits_passed")
        ):
            return None
        plan, schedule, arms = collect(run)
        rows = arms.get("baseline", {})
        if len(rows) != study["counts"][task]:
            return None
        wanted = {
            row["id"]
            for w in plan["workers"]
            if w["arm"] == "baseline"
            for row in json.loads((run / w["split"]).read_text())["tasks"][task]["evaluation"]
        }
        if {row["id"] for row in rows.values()} != wanted:
            raise ValueError("Baseline IDs differ from the frozen run split")
        if plan["source"] != study["source"]:
            raise ValueError("Baseline source identity differs from its study")
        outcomes[task] = sorted(rows.values(), key=lambda r: r["id"])
        end = json.loads((run / "baseline-complete.json").read_text())
        evidence[task] = {
            "run": name,
            "phase_seconds": datetime.fromisoformat(end["at"]).timestamp()
            - schedule["baseline"]["start_epoch"],
            "plan_sha256": file_digest(run / "plan.json"),
            "status_sha256": file_digest(status),
            "audits_passed": True,
        }
    payload = {
        "version": 1,
        "conditions": conditions(study),
        "counts": study["counts"],
        "outcomes": outcomes,
        "origin": {
            "branch": study["branch"],
            "code_commit": study["code_commit"],
            "source": study["source"],
            "environment": study.get("environment"),
            "tasks": evidence,
        },
    }
    wrapper = {"payload": payload, "sha256": digest(payload)}
    destination = Path(destination)
    if destination.exists():
        if read_reference(destination) != wrapper:
            raise ValueError("Refusing to replace an immutable frozen baseline")
    else:
        atomic_json(destination, wrapper)
    return wrapper


def score(reference, task):
    rows = reference["payload"]["outcomes"][task]
    return {"n": len(rows), "correct": sum(bool(r["correct"]) for r in rows)}


def compare(reference, run, task):
    _, _, arms = collect(run)
    base = {r["task"] + "/" + r["id"]: r for r in reference["payload"]["outcomes"][task]}
    ours = arms.get("ours", {})
    if not set(ours) <= set(base):
        raise ValueError("Ours contains IDs outside the frozen baseline")
    return summarize_vs_baseline({"baseline": base, "ours": ours}, [task])["ours"][task]


def public_reference(reference):
    """Portable reference contains no private storage paths; retain original source hashes."""
    return copy.deepcopy(reference)
