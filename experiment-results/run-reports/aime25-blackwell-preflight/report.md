# Lost Tokens — smoke validation (not benchmark scores)

Updated: 2026-10-29T15:49:02.554511+00:00

| Task | Common n | baseline | ours | Difference pp |
|---|---:|---:|---:|---:|
| aime25 | 1 | 0.00% (0) | 0.00% (0) | +0.00 |
| all | 1 | 0.00% (0) | 0.00% (0) | +0.00 |

Paired performance against baseline:

| Arm | Task | Common n | Timed n | Baseline mean s | Arm mean s | Time change | Baseline body tok/s | Arm body tok/s | Forward-token change |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ours | aime25 | 1 | 0 | pending | pending | pending | pending | pending | +18.82% |
| ours | all | 1 | 0 | pending | pending | pending | pending | pending | +18.82% |

Positive time change means slower; negative means faster.

Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.

Parallel phase wall seconds (loading included, final audits excluded): {"baseline": 33.13319277763367, "ours": 33.11023783683777}.

Own completed: baseline 1, ours 1.

Common completed sets are completion-selected when a time budget is used.
32K-input LongBench is not a full-context official benchmark score.
Selected-rollout commit changes the main continuation as well as alternative memory.
Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.
