# Matched ordinary AR baseline

The original baseline is plain AR, without branching or memory. Seed 95021, pinned Qwen3-4B-Thinking-2507, BF16, vLLM 0.10.2 V0, temperature 0.6, top-p 0.95, top-k 20 and 32,768 output tokens. The repository repetition guard is enabled for both conditions. Original historical runs and immutable references are retained.

| Dataset | Correct / full n | Accuracy | Original phase wall (min) |
|---|---:|---:|---:|
| aime25 | 21/30 | 70.00% | 9.19 |
| gpqa | 275/448 | 61.38% | 29.22 |
| gsm8k | 1258/1319 | 95.38% | 10.71 |
| hmmt25 | 15/30 | 50.00% | 10.19 |
| math500 | 489/500 | 97.80% | 28.22 |
| mmlu | 11438/14042 | 81.46% | 209.26 |

Frozen baseline reference SHA256: `6ddd1f83caa9faff8fb016c4c91a04f30cbe95a192e5e775cf92c62b8d7bf7ef`. It uses corrected scoring on original saved responses. The full reference is in the detailed shared archive, with original source/cohort/runtime provenance. Phase wall times include the original generation phase, not this publication's CPU rescore or GPU smoke tests. Concurrent case times are not summed as wall time.
