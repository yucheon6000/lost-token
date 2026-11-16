# ours: yucheon-memory-2026-11-16

Cohort: `l40s-2h-v1`
Hardware profile: `l40s-4gpu`

Environment: [environment.json](environment.json): GPU model/count/IDs, driver/CUDA, packages, precision and batching.

| Dataset | Correct / completed | Required n | Accuracy | Phase wall (s) | Run state |
|---|---:|---:|---:|---:|---|
| aime25 | 22/30 | 30 | 73.33% | 3565.7 | complete |
| hmmt25 | 12/25 | 25 | 48.00% | 3131.1 | complete |
| gsm8k | 1256/1319 | 1319 | 95.22% | 4464.4 | complete |
| gpqa | 59/90 | 90 | 65.56% | 1885.9 | complete |
| math500 | 124/125 | 125 | 99.20% | 2652.5 | complete |
| mmlu | 436/550 | 550 | 79.27% | 3618.6 | complete |

Incomplete runs and samples are not full-dataset accuracy.
Timing source: each saved report/schedule/arm-complete file; report loading/audit exclusions.

See [summary.md](summary.md) and comparison-vs-previous-ours.json for extracted-answer recovery and paired comparison against the prior Ours. These are not AR baseline deltas.
