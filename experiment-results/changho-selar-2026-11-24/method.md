# SeLaR adaptation: selective latent reasoning

Status: complete at 2026-11-24T06:37:01.581689+09:00; full-suite wall time 8 h 20 min 42 s including preflights. AIME25 +2, HMMT25 tie, other four regress versus matched AR. No overall improvement demonstrated. All native preflights, official coverage and worker/trajectory audits passed.

## Mechanism

A single Qwen3-4B-Thinking-2507 instance maintains one KV trajectory and produces one final answer per case. No answer ensemble, sibling rollouts, separate verifier or second model is used. After sampling the logical token with the unchanged per-position sampler, the thinking phase computes the top-3 distribution from the same temperature/top-k/top-p filtered logits. Its entropy is normalized by log(3). When entropy is at least 0.5, the next transformer input embedding is `u + h*(u-E[top1])`, where `u=sum(p_i*E[i])` and h is normalized entropy. Mixture arithmetic is FP32 and the transformer remains BF16. Other positions receive the normal sampled-token embedding.

Parameters are globally fixed: top-3, entropy threshold 0.5, contrastive coefficient 1.0. Digits, Latin letters, mathematical syntax and special tokens receive the static guard; soft inputs are disabled after the thinking boundary. Gold labels are accessed only after generation by the unchanged scorer. The logical token transcript is saved, but the full mixture metadata is also required to reconstruct the actual model inputs.

This adapts SeLaR (Fu and Luo, ACL 2026; https://aclanthology.org/2026.acl-long.320/ ; official implementation https://github.com/Parker-rfu/SeLaReasoning). It is not a bitwise reproduction: the experiment preserves this repository's exact sampler, per-position seeds, reasoning-only boundary and scorer, uses a single global threshold rather than per-benchmark tuning, and applies the gate independently to every request. Published results do not establish effectiveness for this 4B checkpoint.

## Fair comparison and scope

All six full-v1 cohorts are used: GSM8K 1,319; MATH500 500; AIME25 30; HMMT25 30; GPQA Main 448; MMLU 14,042. IDs and normalized rows are verified against the committed full-set cohort manifest; no subsets are redrawn. Baseline is newly measured ordinary AR with the same eager vLLM engine, disabled prefix caching, sampler, prompt, model revision, data, scorer and 32,768-token output cap. The older CUDA-graph AR results are historical context, not the paired primary reference. Baseline is frozen once per task and reused unchanged.

The two modes are independent conditions, not combined to select an answer. Preflight GSM8K and MMLU runs use 16 stored IDs each solely to validate native final extraction and real soft inputs. Their outcomes are excluded from benchmark scores. Both must pass audits, contain soft inputs, and extract finals in at least 90% of cases before official generation starts. All completed results, including regressions, missing finals and cap hits, are retained.

## vLLM and immutable resume

The allocated eight GPUs each host one independent TP=1 vLLM 0.10.2 V0 model, at most eight live cases per GPU. A request-local embedding hook injects mixtures without extra transformer passes. Continuous batching refills freed slots. Eager execution is required because CUDA graphs bypass Python hooks; prefix caching is disabled because token IDs do not uniquely specify latent KV inputs. Installed packages and shared environments are unchanged.

Every 128 logical tokens, token IDs, seeds, probabilities, entropy, candidate weights, contrastive strength and phase data are saved in a hashed append-only checkpoint chain. Resume validates source/config/runtime/cohort identity, preserves completed case files, and teacher-forces saved tokens with saved input mixtures one decode step at a time. A one-GPU fixed-batch integration probe verified identical resumed tokens and mixture descriptors; dynamic batching may still change future floating-point outputs. No experiment deadline is introduced or reset. The final branch date is the actual completion date in Asia/Seoul.

## Validation and artifacts

186 CPU unittests passed; wheel packaging/import from a different working directory and CLI loading passed. GPU integration probe verified 9 actual mixed inputs over 256 generated tokens and exact fixed-batch replay; that deliberately capped probe is not a native scoring test. The frozen-source native preflights provide the latter. See environment.json, config.json, manifest.json, cohort-manifest.json, status.json, results.md, baselines/, runs/, controller.log and queue-request.json for execution evidence. A failed preflight or worker stops the suite with checkpoints preserved.

## Immutable execution and full settings

Code branch: `changho-selar-2026-11-24`; code commit: `b73de083544f527ec54af7b88045ddfd31307e32`. Full settings are in config.json; package source hashes are in source-identity.json. The paired AR used this same eager/no-prefix-cache engine.
