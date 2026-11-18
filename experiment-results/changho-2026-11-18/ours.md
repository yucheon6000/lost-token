# Ours: five-path and pooled consensus

Completed **2026-11-18 21:27 KST**; all 30 member runs and all worker audits passed. No GPU tasks remain. Final code branch follows the completion date: `changho-2026-11-18`.

**Primary criterion: exceed the frozen AR baseline**, per the updated user instruction. All three complete datasets exceed baseline in both five-path repeats. GPQA improves by only 1–5 correct answers across the repeats, so a reliable generalization effect or statistical significance is not claimed.

| Full dataset | n | Frozen AR | Five paths, repeat 0 | Five paths, repeat 1 | Ten paths pooled | Pooled Δ vs AR (pp) |
|---|---:|---:|---:|---:|---:|---:|
| aime25 | 30 | 21/30 (70.00%) | 24/30 (80.00%) | 25/30 (83.33%) | 26/30 (86.67%) | +16.67 |
| hmmt25 | 30 | 15/30 (50.00%) | 17/30 (56.67%) | 18/30 (60.00%) | 17/30 (56.67%) | +6.67 |
| gpqa | 448 | 275/448 (61.38%) | 280/448 (62.50%) | 276/448 (61.61%) | 278/448 (62.05%) | +0.67 |

Each five-path vote costs five complete trajectories; pooled results use ten. All use the same model, frozen final-answer extractor and complete canonical IDs for the three tasks. This is increased-compute accuracy relative to a single trajectory. The pooled result reuses the two repeats and is not a third independent repeat.

| Group | Dataset | Paired wins / losses vs AR | Ties | Missing answers |
|---|---|---:|---:|---:|
| r0 | aime25 | 3/0 | 5 | 0 |
| r0 | hmmt25 | 2/0 | 4 | 1 |
| r0 | gpqa | 28/23 | 12 | 0 |
| r1 | aime25 | 4/0 | 1 | 0 |
| r1 | hmmt25 | 5/2 | 4 | 0 |
| r1 | gpqa | 28/27 | 18 | 0 |
| pooled | aime25 | 5/0 | 1 | 0 |
| pooled | hmmt25 | 3/1 | 6 | 0 |
| pooled | gpqa | 27/24 | 20 | 0 |

## Decision

The requested empirical baseline-only criterion is met. Keep the five-path roster as the default candidate: both fresh-seed repeats exceed baseline on all three full datasets. Ten paths further improve AIME, while HMMT and GPQA do not show a consistent extra benefit. GPQA margins are small; do not describe the result as guaranteed improvement on unseen problems.

The earlier cached five-path exploration (25/30, 20/30, 289/448) is separate from these fresh-seed results. The five member policies, equal weights, math-equivalence vote, deterministic tie order and two independent seed schedules were frozen before new validation. No reference answers enter selection.

## Scope and recovery

Only AIME25, HMMT25 and GPQA Main were evaluated in this experiment. GSM8K, MATH500 and MMLU were not rerun. Existing shared-v1/L40S cohorts and all historical submissions remain unchanged.

The queue stopped during the first GPQA AR component on Nov 17 because of a vLLM startup port collision. On Nov 18 it resumed using the identical source/configs and original schedule/deadline; all 2,839 existing checkpoint files were verified byte-identical. Stale operational heartbeat statuses were archived and refreshed. The resumed member phase wall includes overnight downtime and must not be presented as active compute time. Raw recovery evidence is included.

[Baseline](baseline.md) · [Method](method.md) · [Environment](environment.json) · [Machine-readable submission](submission.json) · [Votes and member provenance](votes/)
