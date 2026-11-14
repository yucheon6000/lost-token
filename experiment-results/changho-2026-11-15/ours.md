# Ours: rank-1 argmax vs confidence lookahead

두 설정은 모두 `filtered_futures` 메모리 방법이다. baseline 일반 AR과 구분한다.

| 데이터셋 | n | Argmax | Lookahead | Argmax wins / losses |
|---|---:|---:|---:|---:|
| HMMT25 | 30 전체 | 18/30 (60.00%) | 17/30 (56.67%) | 2 / 1 |
| AIME25 | 30 전체 | 24/30 (80.00%) | 21/30 (70.00%) | 3 / 0 |
| GPQA Main | 23 pilot | 11/23 (47.83%) | 11/23 (47.83%) | 3 / 3 |
| MATH500 | 25 pilot | 23/25 (92.00%) | 23/25 (92.00%) | 1 / 1 |
| MMLU | 703 pilot | 554/703 (78.81%) | 558/703 (79.37%) | 18 / 22 |
| GSM8K | 1,319 전체 | 1,261/1,319 (95.60%) | 1,257/1,319 (95.30%) | 11 / 7 |

모든 pair의 평가 ID가 동일함을 확인했다. 12개 run이 complete/audits_passed이며
총 96개 worker audit를 확인했다. 데이터셋을 섞은 평균 정확도로 일반적인 개선을 주장하지 않는다.

## 아티팩트

- 정확한 run 이름/시간: [run-summary.json](run-summary.json)
- source fingerprint: [source-identity.json](source-identity.json), [원본 소스](source-snapshot/lost_tokens/)
- 문제별 정오답: [case-outcomes.jsonl](case-outcomes.jsonl)
- 고정 pilot ID: [pilot-cohort-ids/](pilot-cohort-ids/)
- [실행 환경](environment.md), [worker별 GPU/버전 JSON](environment.json)

HMMT argmax는 scoring-only 장애 복구로 추론 checkpoint 18,484개를 재사용했다.
정확도는 모두 다시 채점·감사했지만 재개 phase의 7분 42초를 fresh 전체 실행시간으로 쓰지 않았다.
기존 생성 checkpoint 이관은 생성 소스/config/split/runtime 동일성을 검증하고 새 identity로 수행했다.

이 pilot의 GPQA/MATH500/MMLU 점수를 새 `shared-v1` 전체/50%/25% 결과로 표기하면 안 된다.
