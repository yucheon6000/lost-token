# ours: yucheon-2026-11-16

Cohort: `l40s-2h-v1`
Hardware profile: `l40s-4gpu`

Environment: [environment.json](environment.json): GPU model/count/IDs, driver/CUDA, packages, precision and batching.

| Dataset | Correct / completed | Required n | Accuracy | Phase wall (s) | Run state |
|---|---:|---:|---:|---:|---|
| aime25 | 25/30 | 30 | 83.33% | 3220.9 | complete |
| hmmt25 | 14/25 | 25 | 56.00% | 2634.9 | complete |
| gsm8k | 1256/1319 | 1319 | 95.22% | 4495.6 | complete |
| gpqa | 51/90 | 90 | 56.67% | 1901.4 | complete |
| math500 | 123/125 | 125 | 98.40% | 3088.1 | complete |
| mmlu | 440/550 | 550 | 80.00% | 3543.6 | complete |

Incomplete runs and samples are not full-dataset accuracy.
Timing source: each saved report/schedule/arm-complete file; report loading/audit exclusions.

See [summary.md](summary.md) and comparison-vs-previous-ours.json for extracted-answer recovery and paired comparison against the prior Ours. These are not AR baseline deltas.
