# Argmax 최종 멀티시드 리포트

최종 완료: 2026-11-28T00:04:05.865557+09:00
**같은 Best 3: 95021 · 95022 · 95023 — 여섯 벤치 모두 완료/audit 통과.**
이 조합은 MMLU 제외 다섯 벤치에서 사후 선택했습니다. 10개 조합 중 승리한 벤치 수 우선, 동률이면 벤치별 Δ(%p)의 동일 비중 평균으로 골랐습니다. MMLU 결과를 보고 다시 고르지 않았습니다. 선택 결과를 무작위·사전 지정 seed의 대표 성능이나 독립적 유의성 검증으로 해석하지 않습니다.

점수는 %, 괄호는 정답/각 방법당 반복 평가 건수, Δ는 %p입니다. 같은 문제를 seed마다 반복한 합계이며 고유 문제 수는 아닙니다.

| 벤치마크 | Best3 Baseline | Best3 Ours | Δ | 전체5 Baseline | 전체5 Ours | Δ |
|---|---:|---:|---:|---:|---:|---:|
| aime25 | 65.56 (59/90) | 77.78 (70/90) | +12.22 | 68.67 (103/150) | 75.33 (113/150) | +6.67 |
| hmmt25 | 51.11 (46/90) | 56.67 (51/90) | +5.56 | 51.33 (77/150) | 56.00 (84/150) | +4.67 |
| gpqa | 61.31 (824/1,344) | 61.61 (828/1,344) | +0.30 | 61.21 (1,371/2,240) | 60.67 (1,359/2,240) | -0.54 |
| gsm8k | 95.12 (3,764/3,957) | 95.27 (3,770/3,957) | +0.15 | 95.09 (6,271/6,595) | 95.34 (6,288/6,595) | +0.26 |
| math500 | 97.93 (1,469/1,500) | 98.13 (1,472/1,500) | +0.20 | 98.04 (2,451/2,500) | 97.96 (2,449/2,500) | -0.08 |
| mmlu | 81.35 (34,269/42,126) | 81.49 (34,328/42,126) | +0.14 | 미측정 | 미측정 | — |

**Best3: 6승0패. 선택 전 전체5: 첫 다섯 벤치에서 3승2패.** MMLU의 다섯 seed 전체 평가는 하지 않았으며, seed42의 별도 완료 결과도 아래 원본에 보존했습니다.

[최종 상세 리포트](final-performance-report.md) · [MMLU 포함 공통3seed JSON](aggregate-results.json) · [10개 조합 전체 순위](selection-report.md) · [실행 환경](environment.json)

## Seed별 원본과 공용 비교표

공용 비교 도구는 single-seed/full-cohort 행을 사용합니다. 이 폴더의 submission.json은 seed95023 한 개의 원본 행이고, 위 표와 aggregate-results.json은 별도의 멀티시드 집계입니다. 반복 평가 합산 분모를 고유 문제 수로 등록하지 않았습니다.

- Seed 95021 (Best3): [changho-argmax-2026-11-16](../changho-argmax-2026-11-16/README.md)
- Seed 95022 (Best3): [changho-argmax-seed95022-2026-11-28](../changho-argmax-seed95022-2026-11-28/README.md)
- Seed 42: [changho-argmax-seed42-2026-11-28](../changho-argmax-seed42-2026-11-28/README.md)
- Seed 95023 (Best3): [changho-argmax-multiseed-2026-11-28](../changho-argmax-multiseed-2026-11-28/README.md)
- Seed 95024: [changho-argmax-seed95024-2026-11-28](../changho-argmax-seed95024-2026-11-28/README.md)

모든 새 결과는 기존의 동결된 matched AR 기준을 유지합니다. 모델 가중치·문제 원문·reasoning·KV cache·대규모 추론 체크포인트는 게시하지 않았습니다. 공개 case artifact는 ID/prediction/correct와 원본 record hash만 포함합니다.

실행/재현 코드: [changho-argmax-selected-mmlu-2026-11-28](https://github.com/yucheon6000/lost-token/tree/changho-argmax-selected-mmlu-2026-11-28), commit `6d83f6789d471fc3960492c7b17d5bbab03a54af`.
