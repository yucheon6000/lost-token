# 전체 실험 비교

정본 브랜치: `shared-evaluation`. 개인 브랜치는 코드·설정만 보관한다.

동일 cohort/모델/backend/seed/채점 조건에서만 방법 간 차이를 해석한다.
L40S 4 GPU/l40s-2h-v1, PRO 6000 8 GPU/shared-v1, 과거 pilot은 분리한다.
[고정 서브셋·하드웨어 프로필](../docs/EVALUATION_PROFILES.md). 미측정 baseline은 다른 방법/과거 점수로 채우지 않는다.

## full-v1

Manifest SHA256: `fa8feb36a037f8bcb4a16a46349c36fef050dabddcc232e5406a2d4733e02c55`
Hardware profile: `full-cohort`

Model: `Qwen/Qwen3-4B-Thinking-2507@768f209d9ea81521153ed38c47d515654e938aea` · backend `vllm` · seed `95021` · `bfloat16`

Scorer: `544e8653b5167cbdd85010401c4214292753eaf4da70d006833369f6c6fd739a` · evaluation settings: `36c329411fce12def62776326e9418ea92b5ac5b656231b38d30d7d7f1e48032`

| Dataset | 제출 / 코드 | 방법 | Baseline (일반 AR) | Ours | Δ %p | GPU | 검증 |
|---|---|---|---:|---:|---:|---|---|
| aime25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus10/pooled | 70.00% (21/30) | 86.67% (26/30) | +16.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r0 | 70.00% (21/30) | 80.00% (24/30) | +10.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r1 | 70.00% (21/30) | 83.33% (25/30) | +13.33 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/argmax | 70.00% (21/30) | 66.67% (20/30) | -3.33 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/argmax | 70.00% (21/30) | 76.67% (23/30) | +6.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus10/pooled | 61.38% (275/448) | 62.05% (278/448) | +0.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r0 | 61.38% (275/448) | 62.50% (280/448) | +1.12 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r1 | 61.38% (275/448) | 61.61% (276/448) | +0.22 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/lookahead | 61.38% (275/448) | 63.17% (283/448) | +1.79 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/lookahead | 61.38% (275/448) | 62.28% (279/448) | +0.89 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gsm8k | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/argmax | 95.38% (1258/1319) | 94.92% (1252/1319) | -0.45 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gsm8k | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/argmax | 95.38% (1258/1319) | 95.53% (1260/1319) | +0.15 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus10/pooled | 50.00% (15/30) | 56.67% (17/30) | +6.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r0 | 50.00% (15/30) | 56.67% (17/30) | +6.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-2026-11-18](changho-2026-11-18/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/7ed439b2ba51d588dae364584e3fbebc8bdcdc54) | consensus5/r1 | 50.00% (15/30) | 60.00% (18/30) | +10.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/argmax | 50.00% (15/30) | 53.33% (16/30) | +3.33 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/argmax | 50.00% (15/30) | 50.00% (15/30) | +0.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| math500 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/lookahead | 97.80% (489/500) | 97.80% (489/500) | +0.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| math500 | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/lookahead | 97.80% (489/500) | 98.60% (493/500) | +0.80 | 8 × RTX PRO 6000 Blackwell | 완료 |
| mmlu | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | local_verification/lookahead | 81.46% (11438/14042) | 81.38% (11427/14042) | -0.08 | 8 × RTX PRO 6000 Blackwell | 완료 |
| mmlu | [changho-disagreement-full-2026-11-20](changho-disagreement-full-2026-11-20/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/fd28c1438fb4e0d31465ff65b33a288185ce5008) | policy_off_control/lookahead | 81.46% (11438/14042) | 81.43% (11435/14042) | -0.02 | 8 × RTX PRO 6000 Blackwell | 완료 |

## full-v1

Manifest SHA256: `fa8feb36a037f8bcb4a16a46349c36fef050dabddcc232e5406a2d4733e02c55`
Hardware profile: `full-cohort`

Model: `Qwen/Qwen3-4B-Thinking-2507@768f209d9ea81521153ed38c47d515654e938aea` · backend `vllm` · seed `95021` · `bfloat16`

Scorer: `8c2da86b956bdb6808005e35073506adb2ec05f60c5c0a794b4bd596342b7c0a` · evaluation settings: `36c329411fce12def62776326e9418ea92b5ac5b656231b38d30d7d7f1e48032`

| Dataset | 제출 / 코드 | 방법 | Baseline (일반 AR) | Ours | Δ %p | GPU | 검증 |
|---|---|---|---:|---:|---:|---|---|
| aime25 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 70.00% (21/30) | 80.00% (24/30) | +10.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 70.00% (21/30) | 70.00% (21/30) | +0.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| aime25 | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 70.00% (21/30) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |
| gpqa | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 57.37% (257/448) | 57.37% (257/448) | +0.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 57.37% (257/448) | 58.26% (261/448) | +0.89 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gpqa | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 57.37% (257/448) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |
| gsm8k | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 95.38% (1258/1319) | 95.60% (1261/1319) | +0.23 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gsm8k | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 95.38% (1258/1319) | 95.30% (1257/1319) | -0.08 | 8 × RTX PRO 6000 Blackwell | 완료 |
| gsm8k | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 95.38% (1258/1319) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |
| hmmt25 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 50.00% (15/30) | 60.00% (18/30) | +10.00 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 50.00% (15/30) | 56.67% (17/30) | +6.67 | 8 × RTX PRO 6000 Blackwell | 완료 |
| hmmt25 | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 50.00% (15/30) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |
| math500 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 97.80% (489/500) | 98.00% (490/500) | +0.20 | 8 × RTX PRO 6000 Blackwell | 완료 |
| math500 | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 97.80% (489/500) | 98.60% (493/500) | +0.80 | 8 × RTX PRO 6000 Blackwell | 완료 |
| math500 | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 97.80% (489/500) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |
| mmlu | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/argmax | 81.10% (11388/14042) | 80.95% (11367/14042) | -0.15 | 8 × RTX PRO 6000 Blackwell | 완료 |
| mmlu | [changho-full-2026-11-15](changho-full-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | filtered_futures/lookahead | 81.10% (11388/14042) | 81.39% (11429/14042) | +0.29 | 8 × RTX PRO 6000 Blackwell | 완료 |
| mmlu | [changho-full-baseline-2026-11-15](changho-full-baseline-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/204b01c7ee62027115be4d5456bb49acc5d382ed) | plain_ar | 81.10% (11388/14042) | 미측정 | — | 8 × RTX PRO 6000 Blackwell | baseline 완료 · ours 미측정 |

## l40s-2h-v1

Manifest SHA256: `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`
Hardware profile: `l40s-4gpu`

Model: `Qwen/Qwen3-4B-Thinking-2507@768f209d9ea81521153ed38c47d515654e938aea` · backend `vllm` · seed `95021` · `bfloat16`

Scorer: `8c2da86b956bdb6808005e35073506adb2ec05f60c5c0a794b4bd596342b7c0a` · evaluation settings: `36c329411fce12def62776326e9418ea92b5ac5b656231b38d30d7d7f1e48032`

| Dataset | 제출 / 코드 | 방법 | Baseline (일반 AR) | Ours | Δ %p | GPU | 검증 |
|---|---|---|---:|---:|---:|---|---|
| aime25 | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 70.00% (21/30) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| aime25 | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 83.33% (25/30) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| aime25 | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 73.33% (22/30) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gpqa | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 56.67% (51/90) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gpqa | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 56.67% (51/90) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gpqa | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 65.56% (59/90) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gsm8k | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 95.38% (1258/1319) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gsm8k | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 95.22% (1256/1319) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| gsm8k | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 95.22% (1256/1319) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| hmmt25 | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 52.00% (13/25) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| hmmt25 | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 56.00% (14/25) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| hmmt25 | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 48.00% (12/25) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| math500 | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 98.40% (123/125) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| math500 | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 98.40% (123/125) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| math500 | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 99.20% (124/125) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| mmlu | [yucheon-2026-11-15](yucheon-2026-11-15/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/0e7fa67be2a776f312af8fe552e70b3906e5e34b) | filtered_futures/lookahead | 미측정 | 80.00% (440/550) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| mmlu | [yucheon-2026-11-16](yucheon-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2309ee4da32203ae0ca2b741907029c2f9c81d9d) | filtered_futures/lookahead | 미측정 | 80.00% (440/550) | — | 4 × L40S | ours 완료 · baseline 미측정 |
| mmlu | [yucheon-memory-2026-11-16](yucheon-memory-2026-11-16/method.md) / [code](https://github.com/yucheon6000/lost-token/tree/2c8b4870afab764f51cf5092467add4a3832f801) | filtered_futures/lookahead | 미측정 | 79.27% (436/550) | — | 4 × L40S | ours 완료 · baseline 미측정 |

## pilot-2026-11-14

Manifest SHA256: `a8d0f0ea62237aaae2a1634deea3210d20c50d1d8768759afda6f6cd60f2c801`
Hardware profile: `legacy`

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
