"""Validate result submissions and regenerate the shared comparison index (stdlib only)."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("baseline.md", "ours.md", "method.md", "environment.json", "submission.json")


def validate(folder, root=ROOT):
    for name in REQUIRED:
        if not (folder / name).is_file() or not (folder / name).stat().st_size:
            raise ValueError(f"Missing required file: {folder / name}")
    item = json.loads((folder / "submission.json").read_text())
    if item["id"] != folder.name or not re.fullmatch(
        r"[a-z0-9][a-z0-9_-]*-\d{4}-\d{2}-\d{2}", item["id"]
    ):
        raise ValueError("Submission ID must equal its {name}-{date} directory")
    if item["code_branch"] != item["id"] or not re.fullmatch(
        r"[0-9a-f]{40}", item["code_commit"] or ""
    ):
        raise ValueError("A personal code branch and immutable code commit are required")
    if not item.get("cohort_version") or not re.fullmatch(
        r"[0-9a-f]{64}", item.get("cohort_manifest_sha256", "")
    ):
        raise ValueError("Cohort version and manifest SHA256 are required")
    if item["scope"] == "shared":
        path = root / "evaluation/subsets/shared-v1/manifest.json"
        manifest = json.loads(path.read_text())
        if (
            item["cohort_version"] != manifest["version"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["cohort_manifest_sha256"]
        ):
            raise ValueError("Shared submission uses a different frozen manifest")
    elif item["scope"] != "historical-ablation":
        raise ValueError("Unknown scope")
    if not item.get("backend") or not item.get("dtype") or type(item.get("seed")) is not int:
        raise ValueError("Backend, precision and seed are required")
    if not re.fullmatch(r"[0-9a-f]{64}", item.get("scorer_sha256", "")):
        raise ValueError("Scoring identity is required")
    if not re.fullmatch(r"[0-9a-f]{64}", item.get("evaluation_settings_sha256", "")):
        raise ValueError("Evaluation settings identity is required")
    seen = set()
    for row in item["rows"]:
        key = (row["dataset"], row["method"])
        if key in seen:
            raise ValueError("Duplicate dataset/method row")
        seen.add(key)
        if type(row["n_required"]) is not int or row["n_required"] <= 0:
            raise ValueError("Invalid required sample count")
        if type(row["gpu_count"]) is not int or row["gpu_count"] <= 0 or not row["gpu_model"]:
            raise ValueError("GPU model and actual GPU count are required")
        for arm in ("baseline", "ours"):
            score = row.get(arm)
            if score is None:
                continue
            if (
                type(score["n"]) is not int
                or type(score["correct"]) is not int
                or not 0 <= score["correct"] <= score["n"] <= row["n_required"]
            ):
                raise ValueError("Invalid measured score")
        if (
            item["scope"] == "shared"
            and row["n_required"] != manifest["datasets"][row["dataset"]]["n"]
        ):
            raise ValueError("Sample count differs from shared cohort")
    return item


def score(value):
    if not value or not value["n"]:
        return "미측정"
    return f"{100 * value['correct'] / value['n']:.2f}% ({value['correct']}/{value['n']})"


def build(root):
    submissions = [
        validate(p.parent, root)
        for p in sorted((root / "experiment-results").glob("*/submission.json"))
    ]
    lines = [
        "# 전체 실험 비교",
        "",
        "정본 브랜치: `shared-evaluation`. 개인 브랜치는 코드·설정만 보관한다.",
        "",
        "동일 cohort/모델/backend/seed/채점 조건에서만 방법 간 차이를 해석한다.",
        "pilot과 새 shared-v1은 분리한다. 미측정 baseline은 다른 방법/과거 점수로 채우지 않는다.",
        "",
    ]
    fields = [
        "submission",
        "cohort",
        "cohort_sha256",
        "dataset",
        "method",
        "n_required",
        "baseline_correct",
        "baseline_n",
        "ours_correct",
        "ours_n",
        "gpu_count",
        "gpu_model",
        "code_commit",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()

    def group(s):
        return (
            s["cohort_version"],
            s["cohort_manifest_sha256"],
            s["model"],
            s["model_revision"],
            s["backend"],
            s["seed"],
            s["dtype"],
            s["scorer_sha256"],
            s["evaluation_settings_sha256"],
        )

    groups = sorted({group(s) for s in submissions})
    for identity in groups:
        cohort, sha, model, revision, backend, seed, dtype, scorer, evaluation = identity
        lines += [
            f"## {cohort}",
            "",
            f"Manifest SHA256: `{sha}`",
            "",
            f"Model: `{model}@{revision}` · backend `{backend}` · seed `{seed}` · `{dtype}`",
            "",
            f"Scorer: `{scorer}` · evaluation settings: `{evaluation}`",
            "",
            "| Dataset | 제출 / 코드 | 방법 | Baseline (일반 AR) | Ours | Δ %p | GPU | 검증 |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
        items = [(s, row) for s in submissions if group(s) == identity for row in s["rows"]]
        for s, row in sorted(items, key=lambda x: (x[1]["dataset"], x[0]["id"], x[1]["method"])):
            a, b = row.get("baseline"), row.get("ours")
            delta = (
                f"{100 * (b['correct'] / b['n'] - a['correct'] / a['n']):+.2f}"
                if a and b and a["n"] == b["n"] and a["n"]
                else "—"
            )
            complete = (
                a and b and a["n"] == b["n"] == row["n_required"] and row.get("audits_passed")
            )
            status = (
                "완료"
                if complete
                else (
                    "ablation·AR 미측정" if s["scope"] == "historical-ablation" else "부분/미완료"
                )
            )
            link = f"[{s['id']}]({s['id']}/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/{s['code_commit']})"
            gpu = f"{row['gpu_count']} × {row['gpu_model'].replace('NVIDIA ', '').replace(' Server Edition', '')}"
            lines.append(
                f"| {row['dataset']} | {link} | {row['method']} | {score(a)} | {score(b)} | {delta} | {gpu} | {status} |"
            )
            writer.writerow(
                {
                    "submission": s["id"],
                    "cohort": cohort,
                    "cohort_sha256": sha,
                    "dataset": row["dataset"],
                    "method": row["method"],
                    "n_required": row["n_required"],
                    "baseline_correct": a["correct"] if a else "",
                    "baseline_n": a["n"] if a else "",
                    "ours_correct": b["correct"] if b else "",
                    "ours_n": b["n"] if b else "",
                    "gpu_count": row["gpu_count"],
                    "gpu_model": row["gpu_model"],
                    "code_commit": s["code_commit"],
                }
            )
        lines.append("")
    lines += [
        "## 보관 자료",
        "",
        "- [원래 baseline 요약](summaries/baseline-results.md)",
        "- `run-reports/`, `run-logs/`, `incorrect-answers/`는 이전 실험 원본 보관 자료다.",
        "- [새 공통 평가 규약](../docs/EXPERIMENT_GUIDE.md)",
        "- [비교 CSV](comparison.csv)",
        "",
        "이 표는 `tools/results.py index`로 생성한다. 수치 셀을 손으로 수정하지 않는다.",
        "",
    ]
    legacy = root / "experiment-results/summaries/baseline-results.md"
    if legacy.exists():
        lines += [
            "## 이전 Transformers 실행 참고표",
            "",
            "아래는 원본 보관 요약의 당시 점수다. 재채점 전 수치와 이전 설정을 포함하며 위 vLLM/cohort 비교에 합산하지 않는다.",
            "[원본 설정·주의사항](summaries/baseline-results.md)",
            "",
        ]
        lines += [line for line in legacy.read_text().splitlines() if line.startswith("|")]
        lines.append("")
    return "\n".join(lines), stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "index"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--submission", help="{name}-{YYYY-MM-DD}")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "validate":
        paths = (
            [root / "experiment-results" / args.submission]
            if args.submission
            else [p.parent for p in (root / "experiment-results").glob("*/submission.json")]
        )
        for path in paths:
            if path.resolve().parent != (root / "experiment-results").resolve():
                parser.error("Submission must be an immediate result directory")
            validate(path, root)
        print("Validated submissions:", len(paths))
        return
    md, table = build(root)
    for name, text in [("README.md", md), ("comparison.csv", table)]:
        path = root / "experiment-results" / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                raise ValueError(f"Stale comparison index: {path}")
        else:
            path.write_text(text)
    print("Comparison index verified" if args.check else "Comparison index updated")


if __name__ == "__main__":
    main()
