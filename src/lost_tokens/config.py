"""Packaged defaults, validation and configurable runtime storage."""

import copy
import json
from importlib.resources import files
from pathlib import Path
from .recurrent_memory import ARMS, validate_budget_forcing


def load_spec(path=None):
    spec = json.loads(
        Path(path).read_text()
        if path
        else files("lost_tokens").joinpath("default.json").read_text()
    )
    return validate_spec(spec)


def runtime_spec(spec, work_dir, model_cache=None):
    result = copy.deepcopy(spec)
    cache = (
        Path(model_cache).expanduser().resolve()
        if model_cache
        else Path(work_dir).resolve() / "models"
    )
    result["model"]["cache_dir"] = str(cache)
    result["similarity"]["encoder"]["cache_dir"] = str(cache)
    return result


def validate_spec(spec):
    if spec.get("protocol") != "recurrent-reasoning-memory-v4":
        raise ValueError("Wrong protocol")
    if spec["model"].get("enable_thinking") is not True:
        raise ValueError("Thinking must be enabled")
    exp = spec["experiment"]
    if "max_events" in exp or "scan_max_tokens" in exp or "scan_min_tokens" in exp:
        raise ValueError(
            "Use min_branch_interval_tokens; event-count and initial-window limits are not supported"
        )
    for key in (
        "max_output_tokens",
        "branch_tokens",
        "top_k",
        "checkpoint_body_tokens",
        "prefill_chunk_tokens",
        "memory_capacity_tokens",
        "memory_compact_to_tokens",
        "max_event_memory_tokens",
    ):
        if type(exp.get(key)) is not int or exp[key] < 1:
            raise ValueError(f"Invalid {key}")
    if not 0 < exp["min_candidate_probability"] < 0.5:
        raise ValueError("Invalid probability threshold")
    if type(exp["min_branch_interval_tokens"]) is not int or exp["min_branch_interval_tokens"] < 0:
        raise ValueError(
            "min_branch_interval_tokens must be a nonnegative integer; 0 disables spacing"
        )
    for key, floor in (
        ("max_memory_events", 1),
        ("min_branch_body_tokens", 0),
        ("memory_ttl_tokens", 1),
    ):
        value = exp.get(key)
        if value is not None and (type(value) is not int or value < floor):
            raise ValueError(f"Invalid {key}")
    validate_budget_forcing(exp)
    guard = exp["repetition_guard"]
    if type(guard["enabled"]) is not bool:
        raise ValueError("Invalid repetition guard switch")
    for key in ("min_span_tokens", "min_cycles", "max_period_tokens"):
        if type(guard[key]) is not int or guard[key] < 1:
            raise ValueError("Invalid repetition guard limit")
    if guard["min_cycles"] < 2:
        raise ValueError("A single occurrence is not repetition")
    if any(k in exp for k in ("equivalence_threshold", "judge_context_tokens", "anchor_tokens")):
        raise ValueError("Obsolete classifier/suffix configuration is not accepted")
    if exp["selection"] != "argmax" or exp["commit"] != "selected_rollout":
        raise ValueError("Unsupported selection/commit rule")
    similarity = spec["similarity"]
    if not -1 <= similarity["threshold"] <= 1:
        raise ValueError("Invalid cosine threshold")
    if (
        similarity["text_scope"] != "rollout_only"
        or similarity["comparison"] != "retained_candidates"
    ):
        raise ValueError("Unsupported cosine inputs or comparisons")
    if similarity["encoder"]["batch_size"] < 1 or similarity["encoder"]["max_tokens"] < 1:
        raise ValueError("Invalid encoder limits")
    if not 0 <= spec["execution"]["min_development_answer_completion"] <= 1:
        raise ValueError("Invalid development completion threshold")
    if not 0 < exp["top_p"] <= 1 or exp["temperature"] <= 0:
        raise ValueError("Invalid sampling")
    if (
        not 0
        < exp["memory_compact_to_tokens"]
        < exp["memory_capacity_tokens"] - exp["max_event_memory_tokens"]
    ):
        raise ValueError("Require compaction hysteresis and room for every event")
    if not exp["arms"] or len(set(exp["arms"])) != len(exp["arms"]) or set(exp["arms"]) - set(ARMS):
        raise ValueError("Invalid arms")
    if exp.get("budget_forcing") is not None and set(exp["arms"]) != {"plain_ar"}:
        raise ValueError("budget_forcing is only supported for plain_ar")
    if spec["execution"]["workers"] != 1:
        raise ValueError(
            "One worker per run; use distinct run paths/devices for independent workers"
        )
    for key in ("prompt_limit", "shuffle_seed"):
        if type(spec["data"].get(key)) is not int or spec["data"][key] < 1:
            raise ValueError("Invalid data." + key)
    if spec["model"]["dtype"] not in ("float32", "float16", "bfloat16"):
        raise ValueError("Unsupported model dtype")
    if not 0 < spec["model"]["gpu_memory_fraction"] <= 1:
        raise ValueError("GPU memory fraction must be in (0, 1]")
    if type(spec["model"]["threads"]) is not int or spec["model"]["threads"] < 1:
        raise ValueError("Model threads must be positive")
    return spec
