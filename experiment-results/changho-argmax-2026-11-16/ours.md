# Initial argmax: full-set, single-seed release

The promoted main method is `filtered_futures` with **argmax selection** and vLLM. These are the original full-set generations, evaluated with the corrected final-response scorer. No benchmark generation was repeated for this publication.

| Dataset | Full n | Matched AR | Initial ours argmax | Delta correct | Gains / losses |
|---|---:|---:|---:|---:|---:|
| aime25 | 30 | 21/30 (70.00%) | 24/30 (80.00%) | +3 | 3 / 0 |
| gpqa | 448 | 275/448 (61.38%) | 279/448 (62.28%) | +4 | 40 / 36 |
| gsm8k | 1319 | 1258/1319 (95.38%) | 1261/1319 (95.60%) | +3 | 11 / 8 |
| hmmt25 | 30 | 15/30 (50.00%) | 18/30 (60.00%) | +3 | 4 / 1 |
| math500 | 500 | 489/500 (97.80%) | 490/500 (98.00%) | +1 | 5 / 4 |
| mmlu | 14042 | 11438/14042 (81.46%) | 11420/14042 (81.33%) | -18 | 413 / 431 |

**Five datasets improve; MMLU regresses.** Seed 95021 only. This result does not establish multi-seed reliability or statistical significance. The 30-problem AIME25 and HMMT25 differences are only three problems each. There is no dataset-specific argmax/lookahead routing in this table.

All six datasets use the archived full-v1 IDs. The AR reference belongs to the same original backend and evaluation protocol. The newer eager/no-prefix-cache AR measurements used for SeLaR/EM-INF are separate experiments.

GPQA and MMLU final answers were rescored after fixing acceptance of an explicit terminal single-letter box. Both baseline and ours use the same corrected scorer. Raw-to-corrected counts: GPQA AR 257→275, ours 257→279; MMLU AR 11388→11438, ours 11367→11420. These are corrections to unchanged outputs, not newly generated solutions. All original source-case hashes and final predictions were independently checked again for this release.

The method returns one final answer but computes short speculative rollouts and memory prefill. It is not a completed-answer ensemble, and it is not a one-forward-per-token method. Equal output caps do not imply equal compute.

[Baseline](baseline.md) · [Ours](ours.md) · [Method](method.md) · [Environment](environment.json) · [Metrics](metrics.json) · [Provenance](provenance.json) · [Release validation](validation.json)

[Immutable detailed shared archive](https://github.com/yucheon6000/lost-token/tree/shared-evaluation/experiment-results/changho-argmax-2026-11-16)
