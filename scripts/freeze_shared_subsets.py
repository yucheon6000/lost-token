"""Create an immutable, label-blind shared evaluation cohort from pinned prepared rows."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from lost_tokens.config import load_spec
from lost_tokens.core import digest, file_digest
from lost_tokens.data import load_prepared, sources


POLICY = {
    "aime25": (30, 30, ()),
    "hmmt25": (30, 30, ()),
    "gsm8k": (1319, 1319, ()),
    "gpqa": (448, 448, ()),
    "math500": (500, 250, ("subject", "level")),
    "mmlu": (14042, 3511, ("subject",)),
}
VERSION = "shared-v1"


def select_rows(rows, task, count, fields):
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate IDs")
    groups = defaultdict(list)
    for row in rows:
        groups[json.dumps([row[f] for f in fields], ensure_ascii=False)].append(row)
    # Largest-remainder allocation preserves the requested global size exactly.
    quotas = {key: len(group) * count // len(rows) for key, group in groups.items()}
    order = sorted(groups, key=lambda key: (-(len(groups[key]) * count % len(rows)), key))
    for key in order[: count - sum(quotas.values())]:
        quotas[key] += 1

    def rank(row):
        return hashlib.sha256(f"lost-tokens/{VERSION}/{task}/{row['id']}".encode()).hexdigest()

    selected = [
        row
        for key in sorted(groups)
        for row in sorted(groups[key], key=lambda r: (rank(r), r["id"]))[: quotas[key]]
    ]
    return sorted(selected, key=lambda row: row["id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to replace a frozen subset version; choose a NEW version directory")
    spec = load_spec()
    args.output.mkdir(parents=True)
    manifest = {
        "version": VERSION,
        "algorithm": "SHA256 rank within strata; largest remainder quotas",
        "selection_uses_answers": False,
        "data": spec["data"],
        "model": {key: spec["model"][key] for key in ("name", "revision", "enable_thinking")},
        "data_adapter_sha256": file_digest(
            Path(__file__).resolve().parents[1] / "src/lost_tokens/data.py"
        ),
        "datasets": {},
    }
    for task, (full_n, n, fields) in POLICY.items():
        rows = load_prepared(args.work_dir, spec, task)
        if len(rows) != full_n:
            raise ValueError(f"Unexpected full dataset size: {task}")
        selected = select_rows(rows, task, n, fields)
        ids = [row["id"] for row in selected]
        path = args.output / f"{task}.json"
        path.write_text(json.dumps({"ids": ids}, ensure_ascii=False, indent=2) + "\n")
        manifest["datasets"][task] = {
            "full_n": full_n,
            "n": n,
            "fraction": n / full_n,
            "requested_fraction": 0.25 if task == "mmlu" else n / full_n,
            "rounding": "ceil" if task == "mmlu" else "exact",
            "ids_file": path.name,
            "ids_file_sha256": file_digest(path),
            "ids_sha256": digest(ids),
            "selected_rows_sha256": digest(selected),
            "source_definition_sha256": digest(sources()[task]),
            "source_revision": sources()[task]["revision"],
            "strata_fields": list(fields),
            "strata_counts": dict(
                sorted(Counter(json.dumps([r[f] for f in fields]) for r in selected).items())
            ),
        }
        print(task, len(selected), "/", len(rows))
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
