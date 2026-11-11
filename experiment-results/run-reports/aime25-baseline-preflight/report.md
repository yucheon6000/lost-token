# Lost Tokens — smoke validation (not benchmark scores)

Updated: 2026-10-29T15:29:59.483363+00:00

| Task | Common n | baseline | ours | Difference pp |
|---|---:|---:|---:|---:|
| aime25 | 0 | pending | pending | pending |
| all | 0 | pending | pending | pending |

Paired performance against baseline:

| Arm | Task | Common n | Timed n | Baseline mean s | Arm mean s | Time change | Baseline body tok/s | Arm body tok/s | Forward-token change |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ours | aime25 | 0 | 0 | pending | pending | pending | pending | pending | pending |
| ours | all | 0 | 0 | pending | pending | pending | pending | pending | pending |

Positive time change means slower; negative means faster.

Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.

Parallel phase wall seconds (loading included, final audits excluded): {"baseline": null, "ours": null}.

Own completed: baseline 0, ours 0.

Common completed sets are completion-selected when a time budget is used.
32K-input LongBench is not a full-context official benchmark score.
Selected-rollout commit changes the main continuation as well as alternative memory.
Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.
