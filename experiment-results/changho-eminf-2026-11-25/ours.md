# EM-INF full-set results

Completed 2026-11-25T05:32:15.212391+09:00; code `86f0a0eca221227bd9fc638bb5a40164db8b3c2c` on `changho-eminf-2026-11-25`. All six full cohorts and worker audits passed.

| Dataset | Full n | Frozen AR | EM-INF | Delta correct | Gains / losses | Missing finals | Cap hits | Wall min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aime25 | 30 | 21/30 (70.00%) | 23/30 (76.67%) | +2 | 2 / 0 | 6 | 6 | 10.50 |
| hmmt25 | 30 | 16/30 (53.33%) | 15/30 (50.00%) | -1 | 1 / 2 | 9 | 9 | 10.50 |
| gpqa | 448 | 280/448 (62.50%) | 261/448 (58.26%) | -19 | 24 / 43 | 0 | 0 | 25.02 |
| gsm8k | 1319 | 1261/1319 (95.60%) | 1258/1319 (95.38%) | -3 | 10 / 13 | 0 | 0 | 11.02 |
| math500 | 500 | 491/500 (98.20%) | 491/500 (98.20%) | +0 | 2 / 2 | 3 | 3 | 23.56 |
| mmlu | 14042 | 11455/14042 (81.58%) | 11420/14042 (81.33%) | -35 | 411 / 446 | 1 | 0 | 197.16 |

One dataset improves, one ties and four regress against the matched AR. This single-seed configuration does not demonstrate an overall improvement and is not adopted as the default. GPQA loses 19 correct answers (24 gains, 43 losses) with zero missing finals; missing-answer extraction does not account for this loss.

Study wall time 4.698 hours. This includes native preflights and EM-INF only; AR timings belong to their original study. Eight allocated RTX PRO 6000 Blackwell Server Edition GPUs. One complete generation per question per condition; no answer ensemble. Native preflight cases are excluded from benchmark scores.
