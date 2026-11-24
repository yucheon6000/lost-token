# EM-INF — all six full cohorts, frozen matched AR

Updated 2026-11-25T05:32:15.212445+09:00; state=complete

One transformer trajectory and one final answer. FP32 logit-only Adam (3 steps; lr 0.1; entropy threshold 0.3; reverse-KL weight 0.05), then unchanged temperature 0.6 / top-k 20 / top-p 0.95 and repetition guard. No SeLaR, rollouts, verifier, prompt edits or budget forcing. Original AR reference reused unchanged.

| Dataset | Full n | Frozen AR | EM-INF | Δ correct | Gains / losses | State |
|---|---:|---:|---:|---:|---:|---|
| aime25 | 30 | 21/30 (70.00%) | 23/30 (76.67%) | 2 | 2 / 0 | complete |
| hmmt25 | 30 | 16/30 (53.33%) | 15/30 (50.00%) | -1 | 1 / 2 | complete |
| gpqa | 448 | 280/448 (62.50%) | 261/448 (58.26%) | -19 | 24 / 43 | complete |
| gsm8k | 1319 | 1261/1319 (95.60%) | 1258/1319 (95.38%) | -3 | 10 / 13 | complete |
| math500 | 500 | 491/500 (98.20%) | 491/500 (98.20%) | 0 | 2 / 2 | complete |
| mmlu | 14042 | 11455/14042 (81.58%) | 11420/14042 (81.33%) | -35 | 411 / 446 | complete |

## Native GPU preflights — excluded from benchmark scores

| Dataset | Complete | Required | Extracted finals | Optimized tokens | State |
|---|---:|---:|---:|---:|---|
| gsm8k | 16 | 16 | 16 | 5244 | complete |
| mmlu | 16 | 16 | 16 | 21185 | complete |

All six full-v1 cohorts are required. Preflights must pass native answer extraction and optimizer audits before official generation. Completed case files, optimizer metadata and hash-chained 128-token checkpoints are immutable. Resume reconstructs saved discrete KV inputs one decode step at a time; future outputs under dynamic batching are not promised bitwise identical. Baseline timings belong to their original study. Partial scores are provisional; all regressions and missing finals are retained.
