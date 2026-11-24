# EM-INF: single-trajectory inference-time logit optimization

Status: complete at 2026-11-25T05:32:15.212391+09:00; wall time 4.698 hours. All native preflights and full-suite audits passed. One dataset improves, one ties and four regress against the matched AR. This single-seed configuration does not demonstrate an overall improvement and is not adopted as the default. GPQA loses 19 correct answers (24 gains, 43 losses) with zero missing finals; missing-answer extraction does not account for this loss.

## Method and preregistered parameters

At each generated token (thinking and final phases), perform a single transformer forward, detach its output logits in FP32, and optimize only that vector. The objective is entropy(p_new) + 0.05 * KL(p_original || p_new), at unit temperature. Adam moments reset for each token; learning rate 0.1, at most three steps, and stop before an update if entropy is below 0.3 nats. Adam uses beta1=0.9, beta2=0.999 and epsilon=1e-8. Model parameters, KV inputs and embeddings are unchanged. Then use the original per-position sampler: temperature 0.6, top-k 20, top-p 0.95 and the unchanged exact-cycle repetition blocker. Only one discrete token is consumed, one KV trajectory is maintained and one final answer is returned.

This is an adaptation of Agarwal et al., The Unreasonable Effectiveness of Entropy Minimization in LLM Reasoning (NeurIPS 2025), https://arxiv.org/abs/2505.15134 . Official implementation https://github.com/shivamag125/EM_PT , pinned reference commit cafe72e95827c813e619fabd706c46ed5ceb2268. Hyperparameters come from its EM-INF/em_inf_eval.sh. The reference utility uses reverse KL via F.kl_div(input=log(p_new), target=p_original, reduction=batchmean), before its sampler. Our analytic gradients match the fresh autograd Adam optimizer in CPU tests. The reference example uses temperature 0.1 on Qwen2.5; we retain 0.6 and this repository's exact sampler and repetition guard to isolate logit optimization. This is not a bitwise reproduction or a claim of published success on this Qwen3 checkpoint. No parameter tuning against benchmark labels is performed.

The logit-vector function is compiled with torch.compile (full graph, static vocabulary, no CUDA graphs) to fuse vector operations. Compilation changes FP32 reduction order: the integration probe measured maximum logit difference 9.346e-5 and maximum probability difference 1.0405e-9 from eager evaluation on a 151,936-entry diagnostic vector. There is no backward pass through the transformer and no extra transformer forward, sibling rollout, answer ensemble, verifier, budget forcing, SeLaR mixture or prompt modification. Learned weights and installed dependencies remain untouched.

## Full evaluation and frozen baseline

All six full-v1 datasets are required, with exactly the committed IDs and normalized row hashes: AIME25 30, HMMT25 30, GPQA Main 448, GSM8K 1,319, MATH500 500, MMLU 14,042. The canonical shared-v1 files are also verified and never redrawn; this full-set scope follows the user's explicit instruction.

The frozen matched AR reference is reused from the completed SeLaR study, code b73de083544f527ec54af7b88045ddfd31307e32. No fresh baseline responses are generated. Each sealed baseline's digest, source/config/runtime/lock/allocation, full ID coverage, outcome hash and audits are validated. Every original generation, data, scoring and seed module remains byte-identical. The only preexisting package changes are adding the EM-INF defaults and their validation; all old defaults and validation text are checked against the baseline commit. New optimizer/worker modules are isolated additions. Original references are copied byte-for-byte and their hashes remain frozen.

Both conditions use the same pinned Qwen/Qwen3-4B-Thinking-2507 revision 768f209d9ea81521153ed38c47d515654e938aea, BF16, eager vLLM 0.10.2 V0, disabled prefix caching, prompts, scoring, seeds and 32,768-token output cap. Baseline historical timings are labeled as original measurements and excluded from the current EM-INF elapsed time. All six outcomes, including regressions and missing finals, must be reported.

Before official evaluation, native GSM8K and MMLU preflights each use the first 16 stored IDs (two per allocated GPU), retain the full output cap, and must cover all IDs, pass audits, extract final answers in at least 90% of cases, execute real optimizer steps and apply zero soft input embeddings. These diagnostic cases are excluded from benchmark results. A failed preflight stops the suite rather than silently dropping a dataset.

## Hardware, resume and validation

Eight explicitly allocated RTX PRO 6000 Blackwell Server Edition GPUs, one independent TP=1 model per GPU, at most eight simultaneous cases/GPU, GPU memory fraction 0.85. Continuous vLLM batching refills slots. Exact runtime, GPU UUIDs/VRAM/driver, versions and allocation are in environment.json and per-worker identity.json. Frozen source/config/model/data/cohort/uv.lock hashes are in manifest.json.

Every 128 generated tokens, immutable hashed blocks save tokens, per-position seeds, raw/optimized token log-probabilities, pre/post entropy, optimizer step counts and maximum logit change. Adam has no cross-token state. Resume validates identity, teacher-forces saved discrete tokens one decode step at a time, and continues with the original position seeds. Completed cases and hashes are not rewritten. No deadline is introduced or reset. The fixed-batch one-GPU probe verified identical resumed tokens and optimizer metadata; future dynamic batching may still change floating-point results.

194 CPU unittests passed, including all old golden-protocol tests. Wheel packaging, resource loading and controller help were verified from /tmp. The separate 256-token GPU integration probe verified disabled EM reproduces original AR tokens, exact fixed-batch checkpoint replay, real optimization, and zero soft embeddings. That capped probe is not the native final-answer/scoring test. The frozen-source native preflights validate that path before full benchmarks.

Code/settings/tests belong on the personal branch. Its final name uses the actual completion date in Asia/Seoul; paths and checkpoint identity remain unchanged across midnight. Shared publication uses baseline.md, ours.md, method.md and environment.json plus the comparison index, preserving original reference provenance.

## Immutable execution and full settings

Code branch: `changho-eminf-2026-11-25`; code commit: `86f0a0eca221227bd9fc638bb5a40164db8b3c2c`. Full settings are in config.json; package source hashes are in source-identity.json. The paired AR used this same eager/no-prefix-cache engine.
