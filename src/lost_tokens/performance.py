"""Paired inference costs from completed outcomes; no generation or GPU work."""

import math
import statistics
import json
from datetime import datetime
from pathlib import Path


TIMING_NOTE = (
    "Case seconds include generation, auxiliary work and case-level overhead, but exclude "
    "model loading and final audits. They sum worker time, not parallel elapsed wall time. "
    "Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. "
    "Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs."
)


def phase_wall_seconds(run, arm, schedule):
    """Parallel phase elapsed time includes loading and pauses, and excludes final audits."""
    path = Path(run) / (arm + "-complete.json")
    start = schedule.get(arm, {}).get("start_epoch")
    if start is None or not path.exists():
        return None
    completion = json.loads(path.read_text())
    if completion.get("expired_before_resume"):
        return None
    return max(0, datetime.fromisoformat(completion["at"]).timestamp() - start)


def outcome_costs(case, result):
    """Copy existing trace costs into the small per-case outcome for cheap reporting."""
    return {
        "forward_tokens": result["policy_cost"]["forward_tokens"],
        "generator_seconds": result["policy_cost"]["seconds"],
        "embedding_seconds": result["embedding_cost"]["seconds"],
        "candidate_tokens": sum(
            len(p["ids"]) for event in result["events"] for p in event["previews"]
        ),
        "memory_insertions": sum(bool(e["memory_ids"]) for e in result["events"]),
        "recovery_seconds": result["recovery_seconds"],
        "timing_complete": (
            case["timing_checkpoint_hits"] == 0 if "timing_checkpoint_hits" in case else None
        ),
    }


def valid_number(value, positive=False):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0)
    )


def timed(row):
    return row.get("timing_complete") is not False and valid_number(row.get("seconds"), True)


def performance_summary(rows):
    rows = list(rows)
    measured = [r for r in rows if timed(r)]
    seconds = sum(r["seconds"] for r in measured)
    body = (
        sum(r["body_tokens"] for r in measured)
        if measured and all(valid_number(r.get("body_tokens")) for r in measured)
        else None
    )
    return {
        "n": len(rows),
        "timed_n": len(measured),
        "timing_unknown_n": sum(r.get("timing_complete") is None for r in measured),
        "resumed_excluded_n": sum(r.get("timing_complete") is False for r in rows),
        "case_seconds": seconds if measured else None,
        "mean_case_seconds": seconds / len(measured) if measured else None,
        "median_case_seconds": statistics.median(r["seconds"] for r in measured)
        if measured
        else None,
        "body_tokens": body,
        "body_tokens_per_second": body / seconds if body is not None else None,
    }


def compare_performance(baseline, arm):
    """Use the same common cases on both sides; never fill absent measurements with zero."""
    common = sorted(set(baseline) & set(arm))
    measured = [k for k in common if timed(baseline[k]) and timed(arm[k])]
    base = performance_summary(baseline[k] for k in measured)
    other = performance_summary(arm[k] for k in measured)
    ratio = other["case_seconds"] / base["case_seconds"] if measured else None
    throughput_ratio = (
        other["body_tokens_per_second"] / base["body_tokens_per_second"]
        if base["body_tokens_per_second"] and other["body_tokens_per_second"] is not None
        else None
    )
    costs = {}
    for field in (
        "forward_tokens",
        "candidate_tokens",
        "generator_seconds",
        "embedding_seconds",
        "memory_insertions",
        "recovery_seconds",
    ):
        keys = [
            k
            for k in common
            if valid_number(baseline[k].get(field)) and valid_number(arm[k].get(field))
        ]
        b = sum(baseline[k][field] for k in keys)
        a = sum(arm[k][field] for k in keys)
        costs[field] = {
            "n": len(keys),
            "baseline_total": b if keys else None,
            "arm_total": a if keys else None,
            "ratio": a / b if keys and b else None,
            "change_percent": 100 * (a / b - 1) if keys and b else None,
        }
    return {
        "n": len(common),
        "timed_n": len(measured),
        "resumed_excluded_n": sum(
            baseline[k].get("timing_complete") is False or arm[k].get("timing_complete") is False
            for k in common
        ),
        "baseline": base,
        "arm": other,
        "time_ratio": ratio,
        "slowdown_percent": 100 * (ratio - 1) if ratio is not None else None,
        "throughput_ratio": throughput_ratio,
        "throughput_change_percent": 100 * (throughput_ratio - 1)
        if throughput_ratio is not None
        else None,
        "costs": costs,
    }


def performance_vs_baseline(outcomes, tasks):
    if "baseline" not in outcomes:
        return {}
    return {
        arm: {
            task: compare_performance(
                {
                    k: r
                    for k, r in outcomes["baseline"].items()
                    if task == "all" or r["task"] == task
                },
                {k: r for k, r in rows.items() if task == "all" or r["task"] == task},
            )
            for task in [*tasks, "all"]
        }
        for arm, rows in outcomes.items()
        if arm != "baseline"
    }


def performance_markdown(comparisons):
    def number(value, percent=False):
        if value is None:
            return "pending"
        return f"{value:+.2f}%" if percent else f"{value:.2f}"

    lines = [
        "",
        "Paired performance against baseline:",
        "",
        "| Arm | Task | Common n | Timed n | Baseline mean s | Arm mean s | Time change | Baseline body tok/s | Arm body tok/s | Forward-token change |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, tasks in comparisons.items():
        for task, r in tasks.items():
            lines.append(
                f"| {arm} | {task} | {r['n']} | {r['timed_n']} | "
                f"{number(r['baseline']['mean_case_seconds'])} | "
                f"{number(r['arm']['mean_case_seconds'])} | "
                f"{number(r['slowdown_percent'], True)} | "
                f"{number(r['baseline']['body_tokens_per_second'])} | "
                f"{number(r['arm']['body_tokens_per_second'])} | "
                f"{number(r['costs']['forward_tokens']['change_percent'], True)} |"
            )
    return [
        *lines,
        "",
        "Positive time change means slower; negative means faster.",
        "",
        TIMING_NOTE,
    ]
