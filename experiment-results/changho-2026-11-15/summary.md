# changho-2026-11-15: lookahead 제거 실험

**최신 11/18 결과:** [AIME/HMMT/GPQA 전체셋의 5경로 합의 두 번 검증 및 10경로 통합](../changho-2026-11-18/summary.md).
세 셋 모두 수정된 동일 채점 기준의 baseline을 두 번의 5경로 평가에서 초과했다. 추론 비용은 문제당 5회이며, GPQA 차이는 작다.

**이전 전체 6셋 결과:** [Changho baseline / argmax / lookahead 전체 비교](../changho-full-2026-11-15/summary.md).
세 조건 모두 AIME/HMMT/GSM8K/GPQA Main/MATH500/MMLU의 전체 문제를 평가했다.
아래 내용은 이전 pilot의 보관 기록이다.

## 범위와 상태

- vLLM에서 메모리를 사용하는 **argmax vs lookahead** 12개 실행을 비교했다.
- 모두 완료됐고, 실행당 GPU worker 8개의 audit를 통과했다.
- 2026-11-14 17:19 KST 종료. 채점 오류 복구 재개 이후 큐 실행은 약 2시간 56분이었다.
- 이것은 **기존 5% pilot**이다. 새 `shared-v1`(GPQA 전체/MATH500 50%/MMLU 25%) 결과가 아니다.
- 일반 AR baseline 전체평가는 이 배치에 없다. [baseline.md](baseline.md)에 미측정 상태와 과거 참고값을 기록했다.

## 정확도

둘 다 `filtered_futures`이며, 경로 선택 외 모델/seed/prompt/메모리 설정은 같다.

| 데이터셋 | 범위 | Lookahead | Argmax | Argmax − Lookahead | Paired wins / losses |
|---|---|---:|---:|---:|---:|
| HMMT25 | 전체 30 | 56.67% (17/30) | **60.00% (18/30)** | +3.33%p | 2 / 1 |
| AIME25 | 전체 30 | 70.00% (21/30) | **80.00% (24/30)** | +10.00%p | 3 / 0 |
| GPQA Main | 약 5%, 23 | 47.83% (11/23) | 47.83% (11/23) | 0.00%p | 3 / 3 |
| MATH500 | 5%, 25 | 92.00% (23/25) | 92.00% (23/25) | 0.00%p | 1 / 1 |
| MMLU | 약 5%, 703 | **79.37% (558/703)** | 78.81% (554/703) | −0.57%p | 18 / 22 |
| GSM8K | 전체 1,319 | 95.30% (1,257/1,319) | **95.60% (1,261/1,319)** | +0.30%p | 11 / 7 |

AIME/HMMT/GSM8K에서 argmax가 높았고 MMLU에서는 낮았다. 단일 seed와 작은 표본의
결과이므로 일괄적인 개선이나 통계적 유의성을 주장하지 않는다. GPQA/MATH500은 정답 수가
같아도 맞힌 문제 집합이 달랐다. 과거 Transformers 점수와 섞어 backend 효과를 방법 효과로 해석하지 않는다.

## 시간 (8 GPU, 모델 로딩 포함·최종 감사 제외)

| 데이터셋/범위 | Argmax | Lookahead |
|---|---:|---:|
| HMMT25 전체 | 체크포인트 복구 실행이므로 비교 제외 | 17분 27초 |
| AIME25 전체 | 14분 42초 | 15분 12초 |
| GPQA 23개 | 4분 26초 | 4분 26초 |
| MATH500 25개 | 6분 56초 | 7분 11초 |
| MMLU 703개 | 20분 28초 | 20분 28초 |
| GSM8K 전체 | 20분 14초 | 20분 44초 |

5% sample phase wall의 단순 비례 전체셋 예상은 설정당 GPQA 약 1시간 26분,
MATH500 약 2시간 20분~24분, MMLU 약 6시간 49분이다. 이는 실측 전체셋 시간이 아니며
초기화 비용, 작은 샘플의 낮은 batch concurrency, 문항 길이/straggler 때문에 오차가 크다.
새 50%/25% 고정셋은 아직 실행하지 않았다.

## 재현과 증거

- [방법](method.md), [ours 상세](ours.md), [환경](environment.md), [환경 JSON](environment.json)
- [정확도·paired 비교 CSV](results.csv), [실행별 시간/상태](run-summary.json)
- [4,260개 문제별 결과](case-outcomes.jsonl), [감사 요약](audit-summary.json)
- [pilot 고정 IDs](pilot-cohort-ids/manifest.json), [source identity](source-identity.json)
- `reports/<run>/`의 report/status/schedule/arm-complete JSON과 `source-snapshot/`의 원본 소스.

GPU별 runtime은 실행 당시 identity에서 추출했다. 드라이버/전체 하드웨어 inventory를
나중에 추가 수집한 값은 environment.json의 `observed_after_runs`에 따로 표시했다.
