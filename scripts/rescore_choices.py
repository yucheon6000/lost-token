"""Rescore saved final responses without loading a model or changing run artifacts.

Run with the project environment: uv run --frozen python scripts/rescore_choices.py
RUN ... --output NEW_JSON. Use --include-math to also rescore math cases.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from lost_tokens.core import digest, extract_choice, file_digest
from lost_tokens.math_scoring import math_correct, natural_answer


def rescore_run(run, include_math=False):
    run = Path(run).resolve()
    counts = Counter()
    changes, inputs, seen = [], [], set()
    paths = sorted(run.glob("workers/*/cases/evaluation/**/*.json"))
    if not paths:
        raise ValueError(f"No saved evaluation cases found: {run}")
    for path in paths:
        # Bind provenance to the exact bytes that were scored.
        raw = path.read_bytes()
        inputs.append(
            {"path": str(path.relative_to(run)), "sha256": hashlib.sha256(raw).hexdigest()}
        )
        case = json.loads(raw)
        for arm, result in case["conditions"].items():
            key = (case["task"], case["id"], arm)
            if key in seen:
                raise ValueError(f"Duplicate evaluation case: {key}")
            seen.add(key)
            is_math = case.get("answer_format") == "math"
            if is_math and not include_math:
                counts["skipped_math"] += 1
                continue
            # Never inspect body_text: it can contain an unfinished scratchpad.
            text = result["answer_text"]
            prediction = (
                natural_answer(text, case) if is_math else extract_choice(text, case["choices"])
            )
            correct = (
                (math_correct(case["gold"], prediction) if is_math else prediction == case["gold"])
                if prediction is not None
                else False
            )
            counts["total"] += 1
            counts["before_correct"] += bool(result["correct"])
            counts["after_correct"] += correct
            counts["before_missing"] += result["prediction"] is None
            counts["after_missing"] += prediction is None
            counts["gained"] += correct and not result["correct"]
            counts["lost"] += bool(result["correct"]) and not correct
            if prediction != result["prediction"] or correct != result["correct"]:
                changes.append(
                    {
                        "task": case["task"],
                        "id": case["id"],
                        "condition": arm,
                        "gold": case["gold"],
                        "before_prediction": result["prediction"],
                        "after_prediction": prediction,
                        "before_correct": result["correct"],
                        "after_correct": correct,
                        "final_response": text,
                        "source_case": str(path.relative_to(run)),
                    }
                )
    return {
        "run": str(run),
        "counts": dict(counts),
        "changes": changes,
        "inputs": inputs,
        "inputs_sha256": digest(inputs),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-math", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new file")
    for run in args.runs:
        if output.is_relative_to(run.resolve()):
            parser.error("Output must be outside the original run directories")
    results = [rescore_run(run, args.include_math) for run in args.runs]
    report = {
        "scope": "Saved final responses; math cases "
        + ("rescored" if args.include_math else "skipped"),
        "scorer_sha256": file_digest(
            Path(__file__).resolve().parents[1] / "src/lost_tokens/core.py"
        ),
        "rescore_script_sha256": file_digest(Path(__file__)),
        "math_scorer_sha256": file_digest(
            Path(__file__).resolve().parents[1] / "src/lost_tokens/math_scoring.py"
        ),
        "runs": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for result in results:
        print(Path(result["run"]).name, json.dumps(result["counts"], sort_keys=True))
    print(f"Saved: {output}")


if __name__ == "__main__":
    main()
