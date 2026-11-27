# Baseline: seed 42

Ordinary AR, without branching or alternative memory; common repetition guard enabled. Reused original sealed results, never rerun for publication.

| Dataset | Correct/full n | Accuracy |
|---|---:|---:|
| aime25 | 21/30 | 70.00% |
| hmmt25 | 17/30 | 56.67% |
| gpqa | 270/448 | 60.27% |
| gsm8k | 1,258/1,319 | 95.38% |
| math500 | 492/500 | 98.40% |
| mmlu | 11,410/14,042 | 81.26% |

Unmeasured benchmarks: none.
The publication envelope has its own hash; each original immutable per-task source seal hash is retained in source_seals.
