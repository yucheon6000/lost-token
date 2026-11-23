"""One allocated GPU worker for a frozen, full-cohort latent/AR condition."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import json
import os
import time

from .config import load_spec, runtime_spec
from .core import RunStore, atomic_json, derived_seed, digest, file_digest, source_fingerprint
from .data import load_prepared
from .latent import LatentTrace, policy, validate_record
from .latent_vllm import LatentModel, LatentProcessor
from .recurrent_memory import instruction, final_response, emitted_marker, reasoning_phase
from .runtime import environment, install_interrupt_handlers


def audit_trajectory(model, trace, prompt, seed, cfg, exp, mode):
    body = []
    thinking = reasoning_phase(model, prompt) == "thinking"
    for token, record in zip(trace.ids, trace.records):
        if token != record["token"] or record["seed"] != derived_seed(seed, "body", len(body)):
            raise ValueError("Latent trace token/seed identity differs")
        validate_record(record, cfg, model.special_ids, model.protected, thinking, mode == "selar")
        marker = emitted_marker(model, (prompt[-32:] + body[-32:])[-32:], token)
        body.append(token)
        if marker:
            thinking = not marker.startswith("</")
    if not trace.terminal or len(body) > exp["max_output_tokens"]:
        raise ValueError("Incomplete or over-budget latent trace")
    if not body or (len(body) < exp["max_output_tokens"] and body[-1] not in model.eos_ids):
        raise ValueError("Latent trace terminated without EOS or its original cap")
    return {
        "tokens": len(body),
        "soft_tokens": sum(r["soft"] for r in trace.records),
        "chain_sha256": trace.root,
        "blocks": trace.blocks,
        "terminal": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "work-dir", "model-cache", "ids-file", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--mode", choices=("ar", "selar"), required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--uv-lock-sha256", required=True)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().absolute())
    install_interrupt_handlers()
    source = source_fingerprint()
    if digest(source) != args.source_sha256:
        raise ValueError("Frozen worker source changed")
    cfg = runtime_spec(load_spec(args.config), args.work_dir, args.model_cache)
    latent = policy(cfg)
    raw = json.loads(args.ids_file.read_text())
    ids = raw["ids"] if isinstance(raw, dict) else raw
    all_rows = load_prepared(args.work_dir, cfg, args.task)
    by_id = {r["id"]: r for r in all_rows}
    if len(ids) != len(set(ids)) or not set(ids) <= by_id.keys():
        raise ValueError("Worker IDs differ from prepared data")
    rows = [by_id[i] for i in ids]
    identity = {
        "source": source,
        "cfg": cfg,
        "mode": args.mode,
        "task": args.task,
        "ids_sha256": digest(ids),
        "rows_sha256": digest(rows),
        "environment": environment(),
        "visible_gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "uv_lock_sha256": args.uv_lock_sha256,
        "deadline_epoch": None,
    }
    worker = RunStore(args.output, identity, resume=args.output.exists())
    model = None
    started = time.time()
    try:
        model = LatentModel(cfg["model"], log=lambda message: print(message, flush=True))

        # Reuse final scoring and the exact legacy prompt; never pass gold to a
        # processor, sampler, mixture policy or input hook.
        def process(row):
            existing = args.output / "outcomes" / (row["id"] + ".json")
            if existing.exists():
                old = json.loads(existing.read_text())
                if (
                    old["id"] != row["id"]
                    or old["mode"] != args.mode
                    or old.get("audits_passed") is not True
                    or old["case_sha256"]
                    != file_digest(args.output / "cases" / (row["id"] + ".json"))
                ):
                    raise ValueError("Completed latent outcome/case changed before resume")
                print("REUSED", row["id"], flush=True)
                return
            path = args.output / "trajectories" / digest(row["id"])
            seed = derived_seed(cfg["experiment"]["seed"], "evaluation/" + row["task"], row["id"])
            case_identity = {
                "worker_identity_sha256": digest(identity),
                "row_sha256": digest(row),
                "seed": seed,
            }
            store = RunStore(path, case_identity, resume=path.exists())
            prompt = model.prompt(instruction(row) + row["question"])
            trace = LatentTrace(store, "trajectory", prompt, latent, args.mode)
            reused = len(trace.ids)
            before = time.monotonic()
            if not trace.terminal:
                processor = LatentProcessor(
                    model, cfg["experiment"], latent, prompt, trace, seed, args.mode == "selar"
                )
                model.engine.submit(processor)
            receipt = audit_trajectory(
                model, trace, prompt, seed, latent, cfg["experiment"], args.mode
            )
            scored = final_response(model, trace.ids, row, model.encode("</think>")[0])
            case = {
                "id": row["id"],
                "task": row["task"],
                "mode": args.mode,
                "seed": seed,
                "body_ids": trace.ids,
                "body_text": model.decode(trace.ids),
                "mixture_records_sha256": digest(trace.records),
                "latent_audit": receipt,
                **scored,
                "seconds": time.monotonic() - before,
                "replayed_tokens": reused,
                "finished_epoch": time.time(),
            }
            atomic_json(args.output / "cases" / (row["id"] + ".json"), case)
            outcome = {
                k: case[k]
                for k in (
                    "id",
                    "task",
                    "mode",
                    "prediction",
                    "correct",
                    "thinking_complete",
                    "seconds",
                    "replayed_tokens",
                    "finished_epoch",
                )
            }
            outcome.update(
                body_tokens=len(trace.ids),
                soft_tokens=receipt["soft_tokens"],
                chain_sha256=trace.root,
                case_sha256=file_digest(args.output / "cases" / (row["id"] + ".json")),
                audits_passed=True,
            )
            atomic_json(args.output / "outcomes" / (row["id"] + ".json"), outcome)
            store.status("complete", audits_passed=True)
            print(
                "COMPLETE",
                row["id"],
                outcome["correct"],
                len(trace.ids),
                receipt["soft_tokens"],
                flush=True,
            )

        pool = ThreadPoolExecutor(max_workers=cfg["model"].get("vllm_batch_size", 8))
        try:
            list(pool.map(process, rows))
        except BaseException:
            model.engine.cancel()
            pool.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            pool.shutdown(wait=True)
        outcomes = [json.loads(p.read_text()) for p in (args.output / "outcomes").glob("*.json")]
        if {r["id"] for r in outcomes} != set(ids):
            raise ValueError("Worker completion does not cover assigned IDs")
        worker.status(
            "complete",
            audits_passed=True,
            n=len(outcomes),
            correct=sum(r["correct"] for r in outcomes),
            elapsed_seconds=time.time() - started,
            engine_metrics=model.engine.metrics,
            finished_at=datetime.now().astimezone().isoformat(),
        )
    except BaseException as exc:
        worker.status(
            "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc)
        )
        raise
    finally:
        if model is not None:
            model.close()


if __name__ == "__main__":
    main()
