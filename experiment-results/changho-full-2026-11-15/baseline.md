# Full-set AR baseline

완료

| Dataset | Correct / full n | Accuracy | Phase wall | Audits |
|---|---:|---:|---:|---|
| hmmt25 | 15/30 | 50.00% | 611.6 s | pass |
| aime25 | 21/30 | 70.00% | 551.4 s | pass |
| gsm8k | 1258/1319 | 95.38% | 642.5 s | pass |
| gpqa | 257/448 | 57.37% | 1753.4 s | pass |
| math500 | 489/500 | 97.80% | 1693.4 s | pass |
| mmlu | 11388/14042 | 81.10% | 12555.9 s | pass |

GPU별 독립 모델, vLLM 0.10.2 V0, BF16, GPU당 동시 case 8개. 시간은 arm 시작부터 완료까지이며 case별 경과 시간을 합산하지 않는다.

환경: [environment.json](environment.json). 완료 시 전체 문제별 결과와 provenance를 고정한다.
