"""Freeze legacy full-cohort scores with the same explicit-choice correction.

Original nonmissing predictions and math scores are unchanged. Only previously
missing choice finals need decoding: the new extractor preserves the precedence
and behavior of every old explicit Final answer match. It adds a terminal box
fallback. Original generations, identities and ledgers are read-only.
"""

import argparse
import copy
import json
from pathlib import Path
import subprocess

from lost_tokens.config import load_spec
from lost_tokens.core import atomic_json, digest, extract_choice, file_digest, source_fingerprint
from lost_tokens.data import load_prepared

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def rescore_outcome(path, schema):
    row = read(path)
    result = {
        **row,
        "original_prediction": row["prediction"],
        "original_correct": row["correct"],
        "source_outcome_sha256": file_digest(path),
    }
    if schema["answer_format"] == "choice" and row["prediction"] is None:
        case_path = path.parents[2] / "cases/evaluation" / row["task"] / path.name
        case = read(case_path)
        condition = next(iter(case["conditions"].values()))
        if condition["prediction"] != row["prediction"] or condition["correct"] != row["correct"]:
            raise ValueError("Original case and outcome disagree")
        prediction = extract_choice(condition["answer_text"], schema["choices"])
        result.update(
            prediction=prediction,
            correct=prediction == row["gold"] if prediction else False,
            source_case_sha256=file_digest(case_path),
        )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy-study", type=Path, required=True)
    p.add_argument("--original-baseline-ref", type=Path, required=True)
    p.add_argument("--cohort-manifest", type=Path, required=True)
    p.add_argument("--pipeline", type=Path, required=True)
    p.add_argument("--work-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Output exists; preserve the frozen comparison")
    pipeline, original = read(args.pipeline), read(args.original_baseline_ref)
    if original["sha256"] != digest(original["payload"]):
        raise ValueError("Original reference hash differs")
    source = source_fingerprint()
    if (
        original["payload"]["conditions"]["scoring_and_seed_sources"]["lost_tokens/math_scoring.py"]
        != source["lost_tokens/math_scoring.py"]
    ):
        raise ValueError("Math scorer changed; cannot silently reuse old grades")
    cohort = read(args.cohort_manifest)
    if (
        file_digest(args.cohort_manifest)
        != original["payload"]["conditions"]["cohort_manifest_sha256"]
    ):
        raise ValueError("Original full-cohort identity differs")
    legacy = read(args.legacy_study)
    comparison, input_hashes, counts = {}, {}, []
    selectors = pipeline["previous_selectors"]
    baseline_rows = {}
    for task in pipeline["benchmarks"]:
        prepared = load_prepared(args.work_dir, load_spec(ROOT / "configs/vllm-argmax.json"), task)
        schemas = {r["id"]: r for r in prepared}
        ids = set(cohort["datasets"][task]["ids"])
        if set(schemas) != ids:
            raise ValueError("Prepared full-cohort IDs differ")
        comparison[task] = {}
        for variant in ("baseline", "argmax", "lookahead"):
            job = next(
                j
                for j in legacy["jobs"]
                if j["task"] == task
                and j["selection" if "selection" in j else "variant"] == variant
            )
            run = Path(job["run_path"])
            if read(run / "status.json").get("audits_passed") is not True:
                raise ValueError("Original run lacks passing audits")
            rows = {}
            for path in run.glob("workers/*/outcomes/*/*.json"):
                ident = read(path)["id"]
                row = rescore_outcome(path, schemas[ident])
                if ident in rows:
                    raise ValueError("Duplicate original case")
                rows[ident] = row
                input_hashes[str(path)] = row["source_outcome_sha256"]
            if set(rows) != ids:
                raise ValueError("Original full-cohort coverage differs")
            entry = {
                "n": len(rows),
                "correct": sum(r["correct"] for r in rows.values()),
                "original_correct": sum(r["original_correct"] for r in rows.values()),
                "cases": {
                    i: {
                        k: r[k]
                        for k in (
                            "prediction",
                            "correct",
                            "original_prediction",
                            "original_correct",
                            "source_outcome_sha256",
                        )
                    }
                    for i, r in rows.items()
                },
            }
            comparison[task][variant] = entry
            counts.append(
                {
                    "task": task,
                    "variant": variant,
                    **{k: entry[k] for k in ("n", "correct", "original_correct")},
                }
            )
            if variant == "baseline":
                frozen = {r["id"]: r for r in original["payload"]["outcomes"][task]}
                if any(
                    frozen[i]["prediction"] != r["original_prediction"]
                    or frozen[i]["correct"] != r["original_correct"]
                    for i, r in rows.items()
                ):
                    raise ValueError("Original frozen AR reference and saved outcomes differ")
                baseline_rows[task] = [
                    {
                        **frozen[i],
                        "original_prediction": r["original_prediction"],
                        "original_correct": r["original_correct"],
                        "prediction": r["prediction"],
                        "correct": r["correct"],
                        "source_outcome_sha256": r["source_outcome_sha256"],
                        **(
                            {"source_case_sha256": r["source_case_sha256"]}
                            if "source_case_sha256" in r
                            else {}
                        ),
                    }
                    for i, r in rows.items()
                ]
            print(
                task,
                variant,
                entry["original_correct"],
                "->",
                entry["correct"],
                "/",
                entry["n"],
                flush=True,
            )
    payload = copy.deepcopy(original["payload"])
    payload.update(
        original_reference_sha256=original["sha256"],
        original_generation_sources=payload["conditions"]["scoring_and_seed_sources"],
        outcomes=baseline_rows,
    )
    payload["conditions"]["scoring_and_seed_sources"] = source
    payload["runs"] = {t: payload["runs"][t] for t in pipeline["benchmarks"]}
    for task in pipeline["benchmarks"]:
        payload["runs"][task]["original_correct"] = payload["runs"][task]["correct"]
        payload["runs"][task]["correct"] = comparison[task]["baseline"]["correct"]
    payload["rescoring"] = {
        "code_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "policy": "missing explicit-choice finals only; unchanged explicit parser precedence and math scorer; no scratchpad parsing",
        "input_outcome_hashes_sha256": digest(input_hashes),
    }
    args.output.mkdir(parents=True)
    atomic_json(
        args.output / "baseline-reference.json", {"payload": payload, "sha256": digest(payload)}
    )
    atomic_json(
        args.output / "previous-study.json", {"selectors": selectors, "comparison": comparison}
    )
    atomic_json(
        args.output / "rescoring-proof.json",
        {
            "scope": payload["rescoring"],
            "source": source,
            "counts": counts,
            "input_hashes": input_hashes,
        },
    )


if __name__ == "__main__":
    main()
