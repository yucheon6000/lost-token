# Baseline 기록

**이번 vLLM pilot 배치의 일반 AR(`plain_ar`) 전체평가는 미측정이다.**
lookahead는 baseline이 아니라, 메모리를 사용하는 기존 ours의 선택 규칙이다.
이번 배치의 primary 비교는 [ours.md](ours.md)에 기록한 argmax vs lookahead이다.
vLLM baseline smoke는 제한된 출력 cap의 구현 검증이므로 benchmark 정확도로 사용하지 않는다.

## 기존 baseline 참고값 — 이번 대조군으로 사용하지 않음

| 데이터셋 | 기존 Transformers baseline | 조건/범위 |
|---|---:|---|
| AIME25 | 80.00% (24/30) | 전체, 반복 억제 ON |
| HMMT25 | 60.00% (18/30) | 전체, 반복 억제 ON |
| GPQA Main | 56.25% (252/448) | 전체, 답 추출 수정 재채점 |
| MATH500 | 97.20% (486/500) | 전체, 학년 서수 처리 재채점 |
| GSM8K | 95.53% (1,260/1,319) | 전체, 반복 억제 ON |
| MMLU | 80.94% (11,366/14,042) | 전체, 이전 반복 억제 OFF |

일부 재채점 전 보고서는 GPQA 248/448, MATH500 485/500을 기록한다.
위 값은 과거 참고값이며 vLLM/새 공통 subset의 matched baseline으로 대체 사용할 수 없다.
기존 원본 보고서는 저장소 `experiment-results/run-reports/`에 있다.

## 향후 공통 평가 baseline

`scripts/shared_eval.py run`은 `shared-v1`의 고정 ID에서 `--arms baseline ours`를 실행한다.
baseline은 일반 AR이며 ours와 model/backend/precision/seed/prompt/scorer/output cap이 같다.
이 matched baseline과 새 공통 ours를 완료하기 전에는 새 cohort에서의 개선을 주장하지 않는다.

환경과 GPU 사용은 [environment.md](environment.md) 및 [environment.json](environment.json)에 기록했다.
이 환경 JSON의 실행 당시 worker identity는 **이번 vLLM ours pilot**에 대한 것이다.
