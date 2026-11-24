# Matched ordinary AR baseline

Complete: 2026-11-24T06:37:01.581689+09:00; code `b73de083544f527ec54af7b88045ddfd31307e32`; completion-date branch `changho-selar-2026-11-24`.

All six datasets use full-v1 IDs and verified normalized rows. Same pinned Qwen3-4B-Thinking-2507 checkpoint, BF16, eager vLLM 0.10.2, disabled prefix caching, sampler, prompt, scorer and 32,768-token cap. Eight RTX PRO 6000 Blackwell Server Edition GPUs, independent TP=1 workers, batch up to eight cases/GPU. Preflights are excluded. See method.md and environment.json.

| Dataset | Full n | Correct | Accuracy | Delta correct vs AR | Missing finals | Cap hits | Mean tokens | Wall min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gsm8k | 1319 | 1261 | 95.60% | +0 | 0 | 0 | 1528.4 | 9.26 |
| math500 | 500 | 491 | 98.20% | +0 | 2 | 2 | 6277.8 | 20.06 |
| aime25 | 30 | 21 | 70.00% | +0 | 6 | 6 | 21431.0 | 10.79 |
| hmmt25 | 30 | 16 | 53.33% | +0 | 9 | 9 | 24543.5 | 9.54 |
| gpqa | 448 | 280 | 62.50% | +0 | 0 | 0 | 8811.1 | 22.34 |
| mmlu | 14042 | 11455 | 81.58% | +0 | 1 | 0 | 3080.4 | 170.22 |

All evaluation jobs and worker/trajectory audits passed. Outcomes and per-task AR references remain immutable. This is a single-seed comparison. AIME25 improves by two cases (three gains, one loss), HMMT25 ties, and the other four datasets regress. The current SeLaR configuration does not demonstrate an overall improvement and is not recommended as the default.

## Audit of AR baseline interventions

No rollouts, memory, verification, budget forcing or latent embeddings are active in AR mode. The configured exact-cycle repetition blocker is not a library-default sampler feature. An offline detector matched against the production guard found zero non-exempt trigger contexts in AIME25, HMMT25, GPQA Main, GSM8K and MATH500. MMLU had two contexts in two cases (one correct, one incorrect); unguarded counterfactual accuracy is unknown. See baseline-guard-audit.json. Sampling uses the Qwen-recommended temperature 0.6, top-p 0.95 and top-k 20 with repository-specific per-position seeds and prompts; this is ordinary AR under the shared protocol, not an assertion of bitwise equivalence to stock vLLM defaults.
