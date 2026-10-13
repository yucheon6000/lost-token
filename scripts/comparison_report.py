#!/usr/bin/env python3
"""Read paired (seed, question) outcomes without combining distinct protocols."""

import argparse
from pathlib import Path

from lost_tokens.core import atomic_json, atomic_text, now
from lost_tokens.reporting import collect, read_json, summarize
from lost_tokens.performance import TIMING_NOTE, performance_markdown, performance_vs_baseline


def report_comparison(root):
    root = Path(root)
    metadata = read_json(root / "comparison.json")
    outcomes = {"baseline": {}, "ours": {}}
    runs = []
    for entry in metadata.get("runs", []):
        path = Path(entry["path"])
        if not (path / "plan.json").exists():
            continue
        plan, schedule, rows = collect(path)
        status = read_json(path / "status.json", {}).get("state", "unknown")
        runs.append({**entry, "state": status, "counts": plan["counts"], "schedule": schedule})
        for key, outcome in rows[entry["arm"]].items():
            parent_deadline = (
                metadata.get("schedule", {}).get(entry["arm"], {}).get("deadline_epoch")
            )
            if parent_deadline is not None and outcome["finished_epoch"] > parent_deadline:
                continue
            paired_key = outcome["task"] + "/seed-" + str(entry["seed"]) + "/" + outcome["id"]
            if paired_key in outcomes[entry["arm"]]:
                raise ValueError("Duplicate seed/question outcome: " + paired_key)
            outcomes[entry["arm"]][paired_key] = {**outcome, "seed": entry["seed"]}
    benchmarks = metadata["identity"]["benchmarks"]
    result = {
        "at": now(),
        "state": metadata["state"],
        "runs": runs,
        "schedule": metadata.get("schedule", {}),
        "paired": summarize(outcomes, benchmarks),
        "performance_vs_baseline": performance_vs_baseline(outcomes, benchmarks),
        "own": {},
        "limitations": [
            "An observation is a seed/question pair; repeated questions are not independent samples.",
            "Incomplete final seed cohorts are time-censored; report full completed seed cohorts separately.",
            "This is a full-method comparison, including prompt, forcing and repetition-guard differences.",
            "Both methods use the same model, precision, sampling, per-seed questions and GPU allocation.",
            TIMING_NOTE,
        ],
    }
    for arm, rows in outcomes.items():
        result["own"][arm] = {}
        for task in [*benchmarks, "all"]:
            selected = [r for r in rows.values() if task == "all" or r["task"] == task]
            result["own"][arm][task] = {
                "n": len(selected),
                "correct": sum(bool(r["correct"]) for r in selected),
                "unique_questions": len({r["id"] for r in selected}),
                "seeds": sorted({r["seed"] for r in selected}),
                "body_tokens": sum(r["body_tokens"] for r in selected),
                "fork_events": sum(r["events"] for r in selected),
                "case_seconds": sum(r["seconds"] for r in selected),
            }
    seeds = sorted({entry["seed"] for entry in runs})
    result["per_seed"] = {}
    for seed in seeds:
        seed_rows = {
            arm: {k: r for k, r in rows.items() if r["seed"] == seed}
            for arm, rows in outcomes.items()
        }
        expected = next(entry["counts"] for entry in runs if entry["seed"] == seed)
        paired = summarize(seed_rows, benchmarks)
        result["per_seed"][str(seed)] = {
            "paired": paired,
            "full_cohort": all(paired[task]["n"] == expected[task] for task in benchmarks),
        }
    lines = [
        "# Plain AR versus sparse reasoning v2",
        "",
        f"State: {result['state']}; updated {result['at']}",
        "",
        "| Task | Common seed/question pairs | Baseline correct/total | Ours correct/total | Delta pp | Wins | Losses |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for task, row in result["paired"].items():
        n = row["n"]
        delta = f"{row['difference_pp']:+.2f}" if n else "pending"
        lines.append(
            f"| {task} | {n} | {row['correct']['baseline']}/{n} | {row['correct']['ours']}/{n} | {delta} | {row['wins']} | {row['losses']} |"
        )
    lines += performance_markdown(result["performance_vs_baseline"])
    lines += ["", *result["limitations"]]
    atomic_json(root / "report.json", result)
    atomic_text(root / "report.md", "\n".join(lines) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(report_comparison(args.root)["paired"])
