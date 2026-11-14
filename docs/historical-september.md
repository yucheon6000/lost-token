# September historical results

Exploratory results through September 22, 2026, using
**Qwen3-4B-Thinking-2507** and the **previous protocol**: 32-token rollouts, every
candidate with probability ≥0.20 rolled out, rank 1 always committed, no preamble.
To reproduce that protocol with the current code, set `branch_tokens: 32`,
`selection: "argmax"`, `lookahead: null` and `memory_preamble: null`; the current
code still rolls out only one alternative, so results will not be identical.
This historical table predates the [latest vLLM pilot](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/experiment-results/changho-2026-11-15/summary.md).
Use the [shared guide](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/EXPERIMENT_GUIDE.md) and its fixed cohorts for new studies. Each historical row compares the
same questions completed by both arms; accuracy includes correct/total counts.
Differences are percentage points.

| Benchmark | Baseline | Ours | Difference |
|---|---:|---:|---:|
| LongBench v2 | **44.86% (48/107)** | 42.06% (45/107) | -2.80 |
| HMMT25 | 43.33% (13/30) | **56.67% (17/30)** | +13.33 |
| GPQA Main | 50.00% (53/106) | **51.89% (55/106)** | +1.89 |
| AIME25 | 70.00% (21/30) | **76.67% (23/30)** | +6.67 |
| SuperGPQA | 41.67% (45/108) | **42.59% (46/108)** | +0.93 |
| **Pooled questions** | **47.24% (180/381)** | **48.82% (186/381)** | **+1.57** |

These runs used 32K input/output caps. HMMT25 and AIME25 cover all 30 questions
each; the other rows are partial evaluations. LongBench v2 uses truncated context.
LongBench v2/HMMT25/GPQA include an additional ours run to complete the shared
cohort, so their compute budgets are unequal. AIME25/SuperGPQA shared a three-hour,
four-GPU budget per arm: baseline completed 183 SuperGPQA questions and ours 108;
the table uses their 108 common questions. The pooled row is question-weighted,
not a benchmark-average score or an equal-compute comparison.

Reports compare **common completed questions**, with per-task accuracy, wins/losses,
completion counts, and runtime. Time-censored subsets can favor quickly completed
questions; they are not full-dataset scores. Selected-rollout commit changes the
main continuation too, so baseline vs ours is not a memory-only ablation.
