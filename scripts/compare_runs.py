#!/usr/bin/env python3
"""Offline paired comparison of arms across run directories (stdlib only).

Usage:
  compare_runs.py RUN [RUN ...] [--arms baseline reference ours] --baseline RUN[:ARM]

Each RUN is a run directory with plan.json and workers/<name>/outcomes/<task>/*.json
(late outcomes past the arm deadline in schedule.json are dropped).
Every (run, arm) pair is compared with the baseline (default: first run, arm
"baseline") on the case ids they have in common.
"""

import argparse
import json
from pathlib import Path


def load(run, arm):
    """Outcomes of one arm, mirroring lost_tokens.reporting.collect()."""
    run = Path(run)
    plan = json.loads((run / "plan.json").read_text())
    schedule_path = run / "schedule.json"
    schedule = json.loads(schedule_path.read_text()) if schedule_path.exists() else {}
    deadline = schedule.get(arm, {}).get("deadline_epoch")
    rows = {}
    for worker in plan["workers"]:
        if worker["arm"] != arm:
            continue
        for path in sorted((run / "workers" / worker["name"] / "outcomes").glob("*/*.json")):
            row = json.loads(path.read_text())
            if deadline is not None and row["finished_epoch"] > deadline:
                continue
            key = row["task"] + "/" + row["id"]
            if key in rows:
                raise ValueError("Duplicate completed case: " + key)
            rows[key] = row
    return rows


def discover_arms(run):
    plan = json.loads((Path(run) / "plan.json").read_text())
    return sorted({w["arm"] for w in plan["workers"]})


def compare(base, other):
    common = sorted(set(base) & set(other))
    n = len(common)
    base_ok = sum(bool(base[k]["correct"]) for k in common)
    other_ok = sum(bool(other[k]["correct"]) for k in common)
    return {
        "n": n,
        "base_correct": base_ok,
        "correct": other_ok,
        "wins": [k for k in common if other[k]["correct"] and not base[k]["correct"]],
        "losses": [k for k in common if base[k]["correct"] and not other[k]["correct"]],
        "diff_pp": 100 * (other_ok - base_ok) / n if n else None,
        "thinking_complete": sum(bool(other[k].get("thinking_complete")) for k in common),
        "base_thinking_complete": sum(bool(base[k].get("thinking_complete")) for k in common),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--arms", nargs="+", help="Arm names to compare (default: all found)")
    parser.add_argument("--baseline", help="RUN[:ARM]; default first run, arm baseline")
    args = parser.parse_args(argv)
    if args.baseline:
        base_run, _, base_arm = args.baseline.partition(":")
        base_run, base_arm = Path(base_run), base_arm or "baseline"
    else:
        base_run, base_arm = args.runs[0], "baseline"
    base = load(base_run, base_arm)
    print(f"Baseline: {base_run} [{base_arm}] ({len(base)} cases)\n")
    print("| Run | Arm | Common n | Baseline | Arm acc | Wins | Losses | Diff pp | Think done (base/arm) |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    details = []
    for run in args.runs:
        for arm in args.arms or discover_arms(run):
            if Path(run) == base_run and arm == base_arm:
                continue
            rows = load(run, arm)
            if not rows:
                continue
            r = compare(base, rows)
            if r["n"]:
                cells = (
                    f"{100 * r['base_correct'] / r['n']:.2f}% ({r['base_correct']}) | "
                    f"{100 * r['correct'] / r['n']:.2f}% ({r['correct']}) | "
                    f"{len(r['wins'])} | {len(r['losses'])} | {r['diff_pp']:+.2f}"
                )
            else:
                cells = "- | - | 0 | 0 | -"
            print(
                f"| {run.name} | {arm} | {r['n']} | {cells} | "
                f"{r['base_thinking_complete']}/{r['thinking_complete']} |"
            )
            details.append((run.name, arm, r))
    for name, arm, r in details:
        print(f"\n{name} [{arm}] wins: {', '.join(r['wins']) or '-'}")
        print(f"{name} [{arm}] losses: {', '.join(r['losses']) or '-'}")


if __name__ == "__main__":
    main()
