"""User-facing commands; all paths and compute allocation are explicit inputs."""

import argparse
import json
from pathlib import Path

from .config import load_spec, runtime_spec
from .data import download_datasets, download_models, prepare, sources
from .reporting import read_json, report
from .runner import audit_run, create_run, supervise, worker


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lost-tokens", description="Unchosen reasoning branches as in-context memory"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "download", "prepare", "run", "smoke", "quickstart"):
        sub = commands.add_parser(name)
        sub.add_argument(
            "--work-dir",
            type=Path,
            default=Path("workspace"),
            help="Storage root relative to the current directory",
        )
        sub.add_argument("--model-cache", type=Path, help="Optional shared Hugging Face cache")
        sub.add_argument(
            "--config", type=Path, help="JSON config; defaults to packaged configuration"
        )
        sub.add_argument("--benchmarks", nargs="+", choices=[*sources(), "all"], default=["aime25"])
        if name == "download":
            sub.add_argument("--data-only", action="store_true")
        if name in ("run", "smoke", "quickstart"):
            sub.add_argument(
                "--gpus", default="0", help="Comma-separated visible GPU indices, or cpu"
            )
            sub.add_argument("--run-name")
            sub.add_argument("--max-output-tokens", type=int)
        if name == "run":
            sub.add_argument(
                "--hours-per-arm",
                type=float,
                help="Sequential equal wall-time budget per arm; omit for full cohort",
            )
            sub.add_argument(
                "--limit", type=int, help="Seeded subset size per benchmark, identical across arms"
            )
    for name in ("resume", "report", "status", "audit"):
        sub = commands.add_parser(name)
        sub.add_argument("--run", type=Path, required=True)
    commands.add_parser("config")
    internal = commands.add_parser("_worker", help=argparse.SUPPRESS)
    internal.add_argument("--run", type=Path, required=True)
    internal.add_argument("--worker", required=True)
    internal.add_argument("--probe", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "config":
        print(json.dumps(load_spec(), indent=2))
        return
    if args.command == "_worker":
        raise SystemExit(worker(args.run, args.worker, args.probe))
    if args.command in ("resume", "report", "status", "audit"):
        run = args.run.expanduser().resolve()
        if args.command == "resume":
            supervise(run)
        elif args.command == "report":
            print(json.dumps(report(run), indent=2))
        elif args.command == "status":
            print(json.dumps(read_json(run / "status.json"), indent=2))
        else:
            audit_run(run)
        return
    work = args.work_dir.expanduser().resolve()
    spec = runtime_spec(load_spec(args.config), work, args.model_cache)
    benchmarks = (
        list(sources()) if "all" in args.benchmarks else list(dict.fromkeys(args.benchmarks))
    )
    if getattr(args, "max_output_tokens", None) is not None and args.max_output_tokens < 1:
        parser.error("--max-output-tokens must be positive")
    if args.command in ("setup", "download", "quickstart"):
        download_datasets(work, benchmarks)
        if not getattr(args, "data_only", False):
            download_models(spec)
    if args.command in ("setup", "prepare", "quickstart"):
        prepare(work, spec, benchmarks)
    if args.command in ("run", "smoke", "quickstart"):
        run = create_run(
            work,
            spec,
            benchmarks,
            args.gpus,
            getattr(args, "hours_per_arm", None),
            getattr(args, "limit", None),
            args.run_name,
            args.command != "run",
            args.max_output_tokens,
        )
        print("Run:", run, flush=True)
        supervise(run)


if __name__ == "__main__":
    main()
