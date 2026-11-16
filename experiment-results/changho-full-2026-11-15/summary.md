# Changho 전체셋 결과

**Baseline / ours argmax / ours lookahead 세 조건 모두 각 데이터셋의 전체셋이다.**

전체 큐: 2026-11-15T05:50:28.443393+09:00 ~ 2026-11-16T04:33:17.932050+09:00. 새 실행 12개와 기존 전체셋 재사용 6개를 합쳐 18개 조건 모두 완료/audit 통과.

| Dataset | Full n | AR baseline | Ours argmax | Ours lookahead |
|---|---:|---:|---:|---:|
| hmmt25 | 30 | 15/30 (50.00%) | 18/30 (60.00%) | 17/30 (56.67%) |
| aime25 | 30 | 21/30 (70.00%) | 24/30 (80.00%) | 21/30 (70.00%) |
| gsm8k | 1319 | 1258/1319 (95.38%) | 1261/1319 (95.60%) | 1257/1319 (95.30%) |
| gpqa | 448 | 257/448 (57.37%) | 257/448 (57.37%) | 261/448 (58.26%) |
| math500 | 500 | 489/500 (97.80%) | 490/500 (98.00%) | 493/500 (98.60%) |
| mmlu | 14042 | 11388/14042 (81.10%) | 11367/14042 (80.95%) | 11429/14042 (81.39%) |

| Dataset | Ours | Paired n | Wins | Losses | Δ vs AR (%p) |
|---|---|---:|---:|---:|---:|
| hmmt25 | argmax | 30 | 4 | 1 | +10.00 |
| hmmt25 | lookahead | 30 | 3 | 1 | +6.67 |
| aime25 | argmax | 30 | 3 | 0 | +10.00 |
| aime25 | lookahead | 30 | 1 | 1 | +0.00 |
| gsm8k | argmax | 1319 | 11 | 8 | +0.23 |
| gsm8k | lookahead | 1319 | 12 | 13 | -0.08 |
| gpqa | argmax | 448 | 47 | 47 | +0.00 |
| gpqa | lookahead | 448 | 45 | 41 | +0.89 |
| math500 | argmax | 500 | 5 | 4 | +0.20 |
| math500 | lookahead | 500 | 7 | 3 | +0.80 |
| mmlu | argmax | 14042 | 444 | 465 | -0.15 |
| mmlu | lookahead | 14042 | 478 | 437 | +0.29 |

Argmax는 AIME/HMMT/GSM8K에서 더 높았고, lookahead는 GPQA/MATH500/MMLU에서 더 높았다. 단일 seed 결과이며 작은 차이를 확정적인 개선으로 해석하지 않는다.

AIME/HMMT/GSM8K의 두 ours는 이미 완료한 동일 조건의 전체셋을 재사용했다. GPQA/MATH500/MMLU의 두 ours와 일반 AR baseline 6개는 이번 전체셋 큐에서 새로 측정했다. 5% pilot을 전체셋 점수로 환산한 값은 없다.

[Baseline](baseline.md) · [Ours](ours.md) · [방법론](method.md) · [환경](environment.json) · [문제별 paired 비교](comparisons.json)
