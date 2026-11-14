# Lost Tokens — paired evaluation

Updated: 2026-10-29T17:53:57.161353+00:00

| Task | Common n | baseline | Difference pp |
|---|---:|---:|---:|
| hmmt25 | 30 | 60.00% (18) | pending |
| all | 30 | 60.00% (18) | pending |

Paired against baseline (common to baseline and the arm):

| Arm | Task | Common n | Baseline | Arm | Wins | Losses | Difference pp |
|---|---|---:|---:|---:|---:|---:|---:|

Parallel phase wall seconds (loading included, final audits excluded): {"baseline": 1507.9302711486816}.

Own completed: baseline 30.

Common completed sets are completion-selected when a time budget is used.
32K-input LongBench is not a full-context official benchmark score.
Selected-rollout commit changes the main continuation as well as alternative memory.
Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.
