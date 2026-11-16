# Changho 전체셋 선택 규칙 ablation

질문: confidence 기반 lookahead 선택을 argmax 고정 선택으로 바꾸면 대안 추론 메모리의 성능이 개선되는가?

코드 브랜치 `changho-2026-11-15`, 재현 가능한 소스와 동일한 코드 commit `204b01c7ee62027115be4d5456bb49acc5d382ed`. 모델/데이터/채점 소스 hash는 source-identity.json, 실제 run 및 worker identity hash는 run-provenance.json에 기록했다.

- Baseline: plain_ar, 분기/대안 메모리 삽입 없음. [기존 전체셋 AR 측정](../changho-full-baseline-2026-11-15/baseline.md)을 그대로 재사용하며 baseline-reference.json도 바이트 단위로 동일하다. Reference hash: `389533293df13ae4eba7c5457dc105cd207768bfddf73ffa6db733f146badb1c`.
- Ours argmax / lookahead: 둘 다 filtered_futures 대안 추론 메모리 방법이다. 선택 규칙만 다르며 전체 config는 configs/에 동결했다. 64-token rollout, 분기 원확률 0.2, 최소 간격 256 body tokens, cosine 0.85, memory 8192/4096, exact selected-rollout commit 및 reasoning-only branching을 유지했다.
- 공통 조건: pinned Qwen3-4B-Thinking-2507, BF16, vLLM 0.10.2 V0, seed 95021, temperature 0.6 / top-p 0.95 / top-k 20, 32768-token prompt/body cap, 반복 억제 ON. GPU 종류/수/UUID/driver/runtime/batching은 environment.json과 reports/*/*/worker-environments.json에 있다.

세 조건 모두 AIME 30, HMMT 30, GSM8K 1319, GPQA Main 448, MATH500 500, MMLU 14042개 전체다. cohort-manifest.json은 원래 전체셋 baseline 제출과 동일하며 정확한 ID/정규화 행 hash를 보존한다. 사용자 요청에 따른 별도 full-v1 그룹이다. 공용 shared-v1, L40S subset이나 과거 5% pilot 결과와 혼합하지 않는다.

AIME/HMMT/GSM8K의 두 ours는 이전 전체셋 실행을 재사용했다. 원래 inference source와 현재 재현 코드의 hash, 각 worker의 config/data/runtime/GPU 배정, 전체 ID coverage 및 완료/audit를 확인했다. 재사용 결과를 새 실행처럼 표기하지 않는다. HMMT argmax는 scoring-fix checkpoint 복구 실행이므로 resume phase wall을 새 실행 시간과 비교하지 않는다. checkpoint-import provenance를 별도 보존했다.

GPQA/MATH500/MMLU의 두 ours는 새로 전체셋을 실행했고 pilot 추론 결과를 이식하지 않았다. 모든 원본 run의 checkpoint/source/config/schedule/deadline은 수정하지 않았다. 18개 조건의 전체 ID 완료 및 audit를 확인했다.

reports/<task>/<variant>/comparison.json은 동일 문제 ID에 대한 paired wins/losses와 baseline 대비 정확도 차이를 기록한다. case-outcomes.jsonl은 ours 두 방법의 문제별 점수/예측/토큰/시간을 보존한다. 시간은 concurrent case elapsed를 합산하지 않고 arm schedule 시작부터 완료까지 측정한다.

관측: argmax가 모든 데이터셋에서 우세하다는 가설은 지지되지 않았다. AIME/HMMT/GSM8K에서는 argmax, GPQA/MATH500/MMLU에서는 lookahead가 더 높았다. 단일 seed와 작은 정답 수 차이에 대한 통계적 확정 주장은 하지 않는다.
