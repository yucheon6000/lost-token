# Lost Tokens — paired evaluation

Updated: 2026-11-01T01:58:25.428887+00:00

| Task | Common n | baseline | Difference pp |
|---|---:|---:|---:|
| gsm8k | 1319 | 95.53% (1260) | pending |
| all | 1319 | 95.53% (1260) | pending |

Paired against baseline (common to baseline and the arm):

| Arm | Task | Common n | Baseline | Arm | Wins | Losses | Difference pp |
|---|---|---:|---:|---:|---:|---:|---:|

Parallel phase wall seconds (loading included, final audits excluded): {"baseline": 3222.976560354233}.

Own completed: baseline 1319.

Common completed sets are completion-selected when a time budget is used.
32K-input LongBench is not a full-context official benchmark score.
Selected-rollout commit changes the main continuation as well as alternative memory.
Case seconds include generation, auxiliary work and case-level overhead, but exclude model loading and final audits. They sum worker time, not parallel elapsed wall time. Resumed partial cases are excluded from paired timing; legacy timing provenance may be unknown. Different output lengths affect tokens/s. Forward tokens are logical work, not GPU FLOPs.
