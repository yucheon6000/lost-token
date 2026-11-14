# 방법론과 재현

## 가설

평균 후속 토큰 로그확률이 높은 경로가 더 정확한 수학 추론이라는 보장은 없다.
대안 메모리는 유지하면서 confidence lookahead 선택을 rank-1 고정으로 바꿔 영향을 분리한다.

## 공통 설정

| 항목 | 값 |
|---|---|
| Model | Qwen/Qwen3-4B-Thinking-2507 |
| Revision | 768f209d9ea81521153ed38c47d515654e938aea |
| Precision / backend | BF16 / vLLM 0.10.2 V0 |
| GPU | RTX PRO 6000 Blackwell Server Edition **8장**, GPU당 독립 모델 |
| TP / case batch | TP=1 / GPU당 최대 8문제 |
| Batch token 상한 / GPU memory fraction | 4,096 / 0.85 |
| Temperature / top-p / top-k | 0.6 / 0.95 / 20 |
| Experiment seed / shuffle seed | 95021 / 20260921 |
| Input / generated body cap | 각각 32,768토큰 |
| Repetition guard | 양쪽 ON |
| Rollout | 64토큰, 상위 후보 원확률 각각 ≥0.2, 최소 간격 256 body tokens |
| Memory | 동일 preamble, cosine threshold 0.85, capacity 8,192 / compact-to 4,096 |

환경 전체는 [environment.md](environment.md), [environment.json](environment.json)에 있다.

## 변경 변수

- Argmax: `selection="argmax"`, `lookahead=null`.
- Lookahead: `selection="lookahead"`, `statistic="mean_logprob"`, `margin=0.1`, `min_tokens=16`.
- 강제 첫 토큰을 제외한 continuation confidence를 비교하는 기존 로직을 유지했다.
- 나머지 메모리/생성/채점 설정은 동일하며 평가 ID와 실행 소스 fingerprint를 검증했다.

## vLLM 구현

`vllm_backend.py`는 버전을 고정한 V0 내부 logits 연결부에서 원 logits를 읽는다.
분기 조건 충족 시 body token을 선택하기 전에 멈추고, 기존 위치별 seed와 top-k/top-p
샘플링을 적용한다. 공유 prefix의 physical KV는 vLLM이 관리하고 각 추론 경로는 독립 ID 이력을 가진다.
선택 rollout을 메모리 뒤에 그대로 commit하는 기존 프로토콜과 audit를 유지했다.
다른 vLLM 버전이나 TP>1에 그대로 호환된다고 주장하지 않는다.

Math-Verify는 signal timeout 때문에 case 작업 스레드에서 직접 실행할 수 없었다.
현재 구현은 spawn한 별도 프로세스의 main thread에서 채점하여 기존 timeout을 유지한다.
단위 테스트 135개, 실제 최종 답 추출/스레드 채점 GPU 경로와 audit를 검증했다.
구현 변경이 없는 짧은 vLLM throughput smoke는 baseline 약 7배, argmax ours 약 5.9배
빨랐지만 긴 문맥/전체셋에 같은 배속을 적용하지 않는다.

## Cohort와 재현 명령

실행은 [개인 코드 브랜치](https://github.com/yucheon6000/lost-token/tree/changho-2026-11-15) checkout에서 한다.
이 공용 브랜치에는 실행 환경/개발 코드를 두지 않는다. 정확한 당시 소스는 source-snapshot의 동결 증거로 보존했다.

당시 AIME/HMMT/GSM8K 전체, GPQA 23개, MATH500 25개, MMLU 703개를 사용했다.
pilot의 작은 subset은 기존 seeded prepared order 앞부분을 선택했으며 새 공통 cohort와 다르다.
정확한 ID/해시는 [pilot-cohort-ids/manifest.json](pilot-cohort-ids/manifest.json)에 보존했다.

다음은 당시 pilot을 재현하는 예다. 모델 캐시가 없으면 같은 config로 setup을 먼저 수행한다.

```bash
uv sync --frozen
uv run --frozen lost-tokens setup --config configs/vllm-argmax.json --benchmarks gpqa
uv run --frozen lost-tokens run --config configs/vllm-argmax.json \
  --benchmarks gpqa --arms ours --gpus 0,1,2,3,4,5,6,7 \
  --ids-file experiment-results/changho-2026-11-15/pilot-cohort-ids/gpqa-ids.json \
  --run-name NAME-DATE-reproduce-gpqa-argmax
# lookahead는 configs/vllm-lookahead.json과 새 run-name을 사용한다.
```

추후 팀 공통 실험은 pilot 명령 대신 [공통 가이드](../../docs/EXPERIMENT_GUIDE.md)의
`shared_eval.py`를 사용한다. 새 기준 GPQA=448, MATH500=250, MMLU=3,511이다.

## 한계와 실패 기록

- 단일 seed, GPQA/MATH500/MMLU는 5% pilot이다. 작은 정답 수 차이는 확정적 결론이 아니다.
- vLLM과 Transformers의 토큰/점수를 동일하게 가정하지 않는다.
- GPU smoke의 짧은 cap 때문에 초기에는 최종 답 채점 스레드 오류를 놓쳤다.
  오류 실행은 보존했고 scoring-only fix 후 새 run으로 검증된 추론 호출만 이관했다.
- case elapsed time은 batching 대기/중첩을 포함한다. 합계를 GPU 시간으로 해석하지 않는다.
- phase wall은 모델 로딩을 포함하고 final audit를 제외한다. 복구 HMMT 시간은 비교에서 제외했다.
- 과거 baseline은 matched vLLM baseline이 아니다. 이번 결과의 primary 비교는 ours 두 선택 규칙이다.
