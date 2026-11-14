"""Fork an untimed run after a scoring-only fix, retaining verified inference calls.

Never changes the source run, its identities, or completed/scored case records.
All generation source files, configurations, splits and runtimes must match.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import time

from lost_tokens.core import RunStore, atomic_json, digest, file_digest, source_fingerprint
from lost_tokens.runner import create_run
from lost_tokens.runtime import environment


INFERENCE_LABEL = re.compile(
    r"/(?:prefill|step-\d+/(?:scan|compact|ttl|force)|"
    r"event-\d+/(?:candidate-\d+|cosine|inject|commit-rollout|complete))$"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    plan = json.loads((source / "plan.json").read_text())
    if plan["seconds_per_arm"] is not None or plan["smoke"]:
        raise ValueError("Only untimed non-smoke inference runs can be forked")
    current = source_fingerprint()
    changed = {
        k for k in current.keys() | plan["source"].keys() if current.get(k) != plan["source"].get(k)
    }
    if changed != {"lost_tokens/math_scoring.py"}:
        raise ValueError(f"Expected a scoring-only source change, got: {changed}")
    for relative, sha in plan["source"].items():
        if file_digest(source / "provenance" / relative) != sha:
            raise ValueError("Original provenance changed")
    spec = json.loads((source / plan["workers"][0]["config"]).read_text())
    run = create_run(
        args.work_dir,
        spec,
        plan["benchmarks"],
        gpus=",".join(plan["gpus"]),
        run_name=args.run_name,
        arms=plan["arms"],
        ids=plan.get("ids"),
    )
    new_plan = json.loads((run / "plan.json").read_text())
    schedule = {arm: {"start_epoch": time.time(), "deadline_epoch": None} for arm in plan["arms"]}
    atomic_json(run / "schedule.json", schedule)
    runtime = environment()
    imports = []
    for assignment in new_plan["workers"]:
        name = assignment["name"]
        old_assignment = next(w for w in plan["workers"] if w["name"] == name)
        old_worker = source / "workers" / name
        old_identity = json.loads((old_worker / "identity.json").read_text())
        cfg = json.loads((run / assignment["config"]).read_text())
        split = json.loads((run / assignment["split"]).read_text())
        if cfg != old_identity["spec"] or digest(split) != old_identity["split_sha256"]:
            raise ValueError("Configuration or normalized split differs")
        if runtime != old_identity["environment"]:
            raise ValueError("Runtime differs from original inference runtime")
        identity = {
            "spec": cfg,
            "source": new_plan["source"],
            "environment": runtime,
            "assignment": assignment,
            "split_sha256": digest(split),
            "plan_sha256": digest(new_plan),
            "schedule": schedule[assignment["arm"]],
            "mode": "study",
        }
        worker = run / "workers" / name
        RunStore(worker, identity)
        dest = worker / "checkpoints"
        dest.mkdir()
        copied = []
        for path in sorted((old_worker / "checkpoints").glob("*.json")):
            raw = path.read_bytes()
            record = json.loads(raw)
            payload = record["payload"]
            if digest(payload) != record["sha256"] or path.stem != digest(
                {"label": payload["label"], "request": payload["request"]}
            ):
                raise ValueError(f"Corrupt source checkpoint: {path}")
            if not INFERENCE_LABEL.search(payload["label"]):
                continue
            (dest / path.name).write_bytes(raw)
            copied.append(
                {"name": path.name, "sha256": file_digest(path), "label": payload["label"]}
            )
        imports.append(
            {
                "worker": name,
                "source_identity_sha256": file_digest(old_worker / "identity.json"),
                "checkpoints": copied,
                "n": len(copied),
            }
        )
    atomic_json(
        run / "checkpoint-import.json",
        {
            "source_run": str(source),
            "source_plan_sha256": file_digest(source / "plan.json"),
            "changed_source_files": sorted(changed),
            "imports": imports,
            "note": "Only content-addressed inference calls imported; final condition/case scoring is recomputed.",
        },
    )
    print(run)
    print("Imported checkpoints:", sum(item["n"] for item in imports))


if __name__ == "__main__":
    main()
