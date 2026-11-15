# 전체셋 일반 AR baseline

사용자가 모든 데이터셋의 전체 평가와 baseline 완료 후 shared-evaluation 게시를 요청했다. baseline 6개가 전체 ID를 완료하고 audit를 통과한 경우에만 게시한다.

코드: `changho-2026-11-15` / `204b01c7ee62027115be4d5456bb49acc5d382ed`. 결과 ID는 기존 pilot을 보존하기 위한 별도 이름이며 실제 실행 코드는 위 브랜치/커밋이다.

방법: plain_ar, 분기/메모리 삽입 없음. pinned Qwen3-4B-Thinking-2507, vLLM 0.10.2 V0, BF16, seed 95021, temperature 0.6, top-p 0.95, top-k 20, 32K body cap, 반복 억제 ON. 전체 설정은 config.json, 소스 hash와 lock hash는 source-identity.json에 있다.

범위: AIME 30, HMMT 30, GSM8K 1319, GPQA Main 448, MATH500 500, MMLU 14042. 기존 shared-v1/l40s cohort를 바꾸지 않은 별도 full-v1 전체셋 결과다. 문제 ID/정규화 행 hash는 cohort-manifest.json에 저장했다.

모든 baseline은 이번 환경에서 새로 측정했다. 과거 pilot이나 Transformers 점수로 대체하지 않았다. 원래 run schedule/deadline과 checkpoint identity를 보존한다. baseline-reference.json은 전체 정오답/예측/조건과 provenance를 hash로 봉인한다. shared-v1 부분셋용 reference로 혼용하지 않는다.

환경: RTX PRO 6000 Blackwell 8장, GPU당 모델 1개/TP=1/case batch=8. UUID·VRAM·드라이버·CUDA·CPU·패키지는 environment.json, 실제 worker 환경은 reports/*/worker-environments.json에 있다. 단일 seed 정확도이며 다른 cohort 점수와 직접 차이를 계산하지 않는다.
