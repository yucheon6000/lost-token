# 전체 실험 비교

정본 브랜치: `shared-evaluation`. 개인 브랜치는 코드·설정만 보관한다.

동일 cohort/모델/backend/seed/채점 조건에서만 방법 간 차이를 해석한다.
pilot과 새 shared-v1은 분리한다. 미측정 baseline은 다른 방법/과거 점수로 채우지 않는다.

## pilot-2026-11-14

Manifest SHA256: `a8d0f0ea62237aaae2a1634deea3210d20c50d1d8768759afda6f6cd60f2c801`

Model: `Qwen/Qwen3-4B-Thinking-2507@768f209d9ea81521153ed38c47d515654e938aea` · backend `vllm-v0-0.10.2` · seed `95021` · `bfloat16`

Scorer: `8c2da86b956bdb6808005e35073506adb2ec05f60c5c0a794b4bd596342b7c0a` · evaluation settings: `36c329411fce12def62776326e9418ea92b5ac5b656231b38d30d7d7f1e48032`

| Dataset | 제출 / 코드 | 방법 | Baseline (일반 AR) | Ours | Δ %p | GPU | 검증 |
|---|---|---|---:|---:|---:|---|---|
| aime25 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 80.00% (24/30) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| aime25 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 70.00% (21/30) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| gpqa | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 47.83% (11/23) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| gpqa | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 47.83% (11/23) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| gsm8k | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 95.60% (1261/1319) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| gsm8k | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 95.30% (1257/1319) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| hmmt25 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 60.00% (18/30) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| hmmt25 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 56.67% (17/30) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| math500 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 92.00% (23/25) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| math500 | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 92.00% (23/25) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| mmlu | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/argmax | 미측정 | 78.81% (554/703) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |
| mmlu | [changho-2026-11-15](changho-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/f1c410b5c248248b8dee91bccf561cf7d911d0e9) | filtered_futures/lookahead | 미측정 | 79.37% (558/703) | — | 8 × RTX PRO 6000 Blackwell | ablation·AR 미측정 |

## 보관 자료

- [원래 baseline 요약](summaries/baseline-results.md)
- `run-reports/`, `run-logs/`, `incorrect-answers/`는 이전 실험 원본 보관 자료다.
- [새 공통 평가 규약](../docs/EXPERIMENT_GUIDE.md)
- [비교 CSV](comparison.csv)

이 표는 `tools/results.py index`로 생성한다. 수치 셀을 손으로 수정하지 않는다.

## 이전 Transformers 실행 참고표

아래는 원본 보관 요약의 당시 점수다. 재채점 전 수치와 이전 설정을 포함하며 위 vLLM/cohort 비교에 합산하지 않는다.
[원본 설정·주의사항](summaries/baseline-results.md)

| Dataset | Baseline accuracy | Ours accuracy | Change | Baseline time | Ours time |
|---|---:|---:|---:|---:|---:|
| AIME25 | 80.00% (24/30) | 83.33% (25/30) | +3.33 pp | 26m 08s | 45m 39s |
| HMMT25 | 60.00% (18/30) | 46.67% (14/30) | -13.33 pp | 25m 08s | 41m 09s |
| GPQA Main | 55.36% (248/448) | 54.69% (245/448) | -0.67 pp | 1h 43m 27s | 2h 21m 45s |
| MATH500 | 97.00% (485/500) | 97.40% (487/500) | +0.40 pp | 1h 32m 57s | 2h 23m 00s |
| MMLU | 80.94% (11,366/14,042)* | Not run | — | 48h 48m 54s | — |
| GSM8K | 95.53% (1,260/1,319)* | Not run | — | 53m 43s | — |
