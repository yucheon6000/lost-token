# Single-stream disagreement verification

Updated 2026-11-20T18:03:07.761608+09:00; state=complete

Each condition generates one solution per question. No completed-answer voting, reranking or best-of-N selection. Verification consumes the same 32K body cap; short speculative candidates and side-input costs are reported separately.

| Dataset | Condition | Completed / full | Correct | Accuracy | Frozen AR on same completed IDs | Wins/losses vs AR | State | Origin |
|---|---|---:|---:|---:|---:|---:|---|---|
| aime25 | verification | 30/30 | 20 | 66.67% | 21/30 | 2/3 | complete | reused audited result |
| aime25 | control | 30/30 | 23 | 76.67% | 21/30 | 4/2 | complete | reused audited result |
| hmmt25 | verification | 30/30 | 16 | 53.33% | 15/30 | 1/0 | complete | reused audited result |
| hmmt25 | control | 30/30 | 15 | 50.00% | 15/30 | 2/2 | complete | reused audited result |
| gpqa | verification | 448/448 | 283 | 63.17% | 275/448 | 36/28 | complete | reused audited result |
| gpqa | control | 448/448 | 279 | 62.28% | 275/448 | 36/32 | complete | reused audited result |
| gsm8k | verification | 1319/1319 | 1252 | 94.92% | 1258/1319 | 5/11 | complete | new generation |
| gsm8k | control | 1319/1319 | 1260 | 95.53% | 1258/1319 | 13/11 | complete | new generation |
| math500 | verification | 500/500 | 489 | 97.80% | 489/500 | 6/6 | complete | new generation |
| math500 | control | 500/500 | 493 | 98.60% | 489/500 | 5/1 | complete | new generation |
| mmlu | verification | 14042/14042 | 11427 | 81.38% | 11438/14042 | 416/427 | complete | new generation |
| mmlu | control | 14042/14042 | 11435 | 81.43% | 11438/14042 | 411/414 | complete | new generation |

Full frozen baseline:
- aime25: 21/30
- gpqa: 275/448
- gsm8k: 1258/1319
- hmmt25: 15/30
- math500: 489/500
- mmlu: 11438/14042

Control and treatment use identical settings and per-position seeds; only the bounded verification task differs. GPU batching can still introduce numerical variability. Both conditions and all failures are retained. Branch dates follow actual completion in Asia/Seoul.
