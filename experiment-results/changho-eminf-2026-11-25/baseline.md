# Frozen matched AR baseline

Original code: `b73de083544f527ec54af7b88045ddfd31307e32`. Reference source study: `/home/user04/ch/workspace/selar-studies/selar-full-2026-11-23`. Original completed measurements are reused without new GPU generation; hashes and full coverage are verified.

| Dataset | Full n | Correct | Accuracy |
|---|---:|---:|---:|
| aime25 | 30 | 21 | 70.00% |
| gpqa | 448 | 280 | 62.50% |
| gsm8k | 1319 | 1261 | 95.60% |
| hmmt25 | 30 | 16 | 53.33% |
| math500 | 500 | 491 | 98.20% |
| mmlu | 14042 | 11455 | 81.58% |

Generator, eager vLLM engine, disabled prefix caching, prompts, sampler, seeds, repetition guard, scorer, data and output cap match the EM-INF condition. Original per-task references are preserved byte-for-byte in baselines/. Timing belongs to the original study. See method.md for compatibility checks and the deliberate optimizer intervention.
