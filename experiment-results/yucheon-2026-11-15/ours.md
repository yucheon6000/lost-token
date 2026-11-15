# ours: yucheon-2026-11-15

Cohort: `l40s-2h-v1`
Hardware profile: `l40s-4gpu`

Environment: [environment.json](environment.json): GPU model/count/IDs, driver/CUDA, packages, precision and batching.

| Dataset | Correct / completed | Required n | Accuracy | Phase wall (s) | Run state |
|---|---:|---:|---:|---:|---|
| aime25 | 21/30 | 30 | 70.00% | 3310.9 | complete |
| hmmt25 | 13/25 | 25 | 52.00% | 3280.2 | complete |
| gsm8k | 1258/1319 | 1319 | 95.38% | 4465.2 | complete |
| gpqa | 51/90 | 90 | 56.67% | 1976.0 | complete |
| math500 | 123/125 | 125 | 98.40% | 3087.4 | complete |
| mmlu | 440/550 | 550 | 80.00% | 3648.5 | complete |

Incomplete runs and samples are not full-dataset accuracy.
Timing source: each saved report/schedule/arm-complete file; report loading/audit exclusions.
