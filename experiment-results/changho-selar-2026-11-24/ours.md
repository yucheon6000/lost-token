# SeLaR full-set results

Completed 2026-11-24T06:37:01.581689+09:00; code `b73de083544f527ec54af7b88045ddfd31307e32` on `changho-selar-2026-11-24`. All six full cohorts and worker audits passed.

| Dataset | Full n | Frozen AR | SeLaR | Delta correct | Gains / losses | Missing finals | Cap hits | Wall min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aime25 | 30 | 21/30 (70.00%) | 23/30 (76.67%) | +2 | 3 / 1 | 6 | 6 | 10.29 |
| hmmt25 | 30 | 16/30 (53.33%) | 16/30 (53.33%) | +0 | 3 / 3 | 7 | 7 | 10.04 |
| gpqa | 448 | 280/448 (62.50%) | 277/448 (61.83%) | -3 | 35 / 38 | 2 | 0 | 22.85 |
| gsm8k | 1319 | 1261/1319 (95.60%) | 1260/1319 (95.53%) | -1 | 11 / 12 | 0 | 0 | 9.77 |
| math500 | 500 | 491/500 (98.20%) | 489/500 (97.80%) | -2 | 2 / 4 | 3 | 3 | 23.33 |
| mmlu | 14042 | 11455/14042 (81.58%) | 11416/14042 (81.30%) | -39 | 418 / 457 | 3 | 0 | 178.02 |

One dataset improves, one ties and four regress against the matched AR. This single-seed configuration does not demonstrate an overall improvement and is not adopted as the default.

Study wall time 8.345 hours. This includes native preflights and the new matched AR measurements. Eight allocated RTX PRO 6000 Blackwell Server Edition GPUs. One complete generation per question per condition; no answer ensemble. Native preflight cases are excluded from benchmark scores.
