"""Read-only paired metrics from immutable, completed case outcomes."""

import json
from pathlib import Path
import time

from .core import atomic_json, now


def read_json(path, default=None):
    for attempt in range(5):
        try:
            return json.loads(Path(path).read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            if attempt == 4:
                if default is not None and not Path(path).exists():
                    return default
                raise
            time.sleep(0.1 * (attempt + 1))


def collect(run):
    run = Path(run)
    plan = read_json(run / "plan.json")
    schedule = read_json(run / "schedule.json", {})
    outcomes = {arm: {} for arm in plan["arms"]}
    for worker in plan["workers"]:
        deadline = schedule.get(worker["arm"], {}).get("deadline_epoch")
        for path in (run / "workers" / worker["name"] / "outcomes").glob("*/*.json"):
            row = read_json(path)
            if deadline is not None and row["finished_epoch"] > deadline:
                continue
            key = row["task"] + "/" + row["id"]
            if key in outcomes[worker["arm"]]:
                raise ValueError("Duplicate completed case: " + key)
            outcomes[worker["arm"]][key] = row
    return plan, schedule, outcomes


def summarize(outcomes, tasks):
    common = sorted(set.intersection(*(set(rows) for rows in outcomes.values())))
    paired = {}
    for task in [*tasks, "all"]:
        keys = [k for k in common if task == "all" or k.startswith(task + "/")]
        correct = {arm: sum(rows[k]["correct"] for k in keys) for arm, rows in outcomes.items()}
        row = {
            "n": len(keys),
            "correct": correct,
            "accuracy": {
                arm: value / len(keys) if keys else None for arm, value in correct.items()
            },
        }
        if "baseline" in outcomes and "ours" in outcomes:
            row["wins"] = sum(
                outcomes["ours"][k]["correct"] and not outcomes["baseline"][k]["correct"]
                for k in keys
            )
            row["losses"] = sum(
                outcomes["baseline"][k]["correct"] and not outcomes["ours"][k]["correct"]
                for k in keys
            )
            row["difference_pp"] = (
                100 * (correct["ours"] - correct["baseline"]) / len(keys) if keys else None
            )
        paired[task] = row
    return paired


def report(run):
    run = Path(run)
    plan, schedule, outcomes = collect(run)
    result = {
        "at": now(),
        "smoke": plan["smoke"],
        "paired": summarize(outcomes, plan["benchmarks"]),
        "own": {},
        "schedule": schedule,
        "limitations": [
            "Common completed sets are completion-selected when a time budget is used.",
            "32K-input LongBench is not a full-context official benchmark score.",
            "Selected-rollout commit changes the main continuation as well as alternative memory.",
        ],
    }
    for arm, rows in outcomes.items():
        result["own"][arm] = {}
        for task in [*plan["benchmarks"], "all"]:
            subset = [r for r in rows.values() if task == "all" or r["task"] == task]
            n = len(subset)
            correct = sum(r["correct"] for r in subset)
            result["own"][arm][task] = {
                "n": n,
                "correct": correct,
                "accuracy": correct / n if n else None,
                "body_tokens": sum(r["body_tokens"] for r in subset),
                "fork_events": sum(r["events"] for r in subset),
                "thinking_complete": sum(r["thinking_complete"] for r in subset),
            }
    lines = [
        "# Lost Tokens — "
        + ("smoke validation (not benchmark scores)" if plan["smoke"] else "paired evaluation"),
        "",
        "Updated: " + result["at"],
        "",
        "| Task | Common n | " + " | ".join(plan["arms"]) + " | Difference pp |",
        "|---|---:|" + "---:|" * len(plan["arms"]) + "---:|",
    ]
    for task, row in result["paired"].items():
        cells = [
            f"{100 * row['accuracy'][a]:.2f}% ({row['correct'][a]})" if row["n"] else "pending"
            for a in plan["arms"]
        ]
        difference = row.get("difference_pp")
        lines.append(
            f"| {task} | {row['n']} | " + " | ".join(cells) + f" | {difference:+.2f} |"
            if difference is not None
            else f"| {task} | {row['n']} | " + " | ".join(cells) + " | pending |"
        )
    lines += [
        "",
        "Own completed: " + ", ".join(f"{a} {len(r)}" for a, r in outcomes.items()) + ".",
        "",
        *result["limitations"],
    ]
    atomic_json(run / "report.json", result)
    from .core import atomic_text

    atomic_text(run / "report.md", "\n".join(lines) + "\n")
    return result
