# Selective latent reasoning — full six-benchmark suite

Updated 2026-11-24T06:37:02.073817+09:00; state=complete

One model, one KV trajectory, one final answer per condition. No complete-response ensemble. Top-3 latent mixture, entropy threshold 0.5, contrastive weight 1.0; same 32768-token cap. A new matched AR reference is measured once with the same eager/no-prefix-cache engine.

| Dataset | Full n | Matched AR | SeLaR | Δ correct | State |
|---|---:|---:|---:|---:|---|
| gsm8k | 1319 | 1261/1319 (95.60%) | 1260/1319 (95.53%) | -1 | AR=complete, SeLaR=complete |
| math500 | 500 | 491/500 (98.20%) | 489/500 (97.80%) | -2 | AR=complete, SeLaR=complete |
| aime25 | 30 | 21/30 (70.00%) | 23/30 (76.67%) | 2 | AR=complete, SeLaR=complete |
| hmmt25 | 30 | 16/30 (53.33%) | 16/30 (53.33%) | 0 | AR=complete, SeLaR=complete |
| gpqa | 448 | 280/448 (62.50%) | 277/448 (61.83%) | -3 | AR=complete, SeLaR=complete |
| mmlu | 14042 | 11455/14042 (81.58%) | 11416/14042 (81.30%) | -39 | AR=complete, SeLaR=complete |

## GPU integration preflights — excluded from benchmark scores

| Dataset | n | Complete | Extracted finals | Soft tokens | State |
|---|---:|---:|---:|---:|---|
| gsm8k | 16 | 16 | 16 | 1681 | complete |
| mmlu | 16 | 16 | 16 | 8373 | complete |

Full sizes and IDs are committed full-v1, not redrawn subsets. All results, including regressions and missing finals, are retained. Latent mixing is thinking-only; math symbols and special/termination tokens remain discrete. Completed checkpoint blocks and mixture weights are immutable. Resume replays saved inputs token by token. Fixed-batch GPU replay is tested; dynamic batching can still change future floating-point results.
