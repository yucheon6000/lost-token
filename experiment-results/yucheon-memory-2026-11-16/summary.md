# Ours with quality-filtered alternative memory

All-six improvement goal achieved: **False**. Results versus latest Ours: 2 gains, 1 ties, 3 losses. This experimental variant is not a universal upgrade.

Only Ours was executed, following the user's standing instruction. No new AR worker was launched.
The primary paired comparison is against latest Ours on L40S. Existing PRO 6000 AR readings are a separately labeled exact-ID reference below.

Code: `yucheon-memory-2026-11-16` / `2c8b4870afab764f51cf5092467add4a3832f801`.
Previous Ours: `yucheon-2026-11-16` / `2309ee4da32203ae0ca2b741907029c2f9c81d9d`.
Hardware: 4 NVIDIA L40S, independent TP=1 workers, BF16, vLLM 0.10.2 V0.
Cohort: `l40s-2h-v1` / `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`.

| Dataset | Correct / n | Accuracy | Previous Ours | Delta vs previous Ours | Phase wall | Audit |
|---|---:|---:|---:|---:|---:|---|
| aime25 | 22/30 | 73.33% | 83.33% | -10.00 pp | 59.4 min | passed |
| hmmt25 | 12/25 | 48.00% | 56.00% | -8.00 pp | 52.2 min | passed |
| gsm8k | 1256/1319 | 95.22% | 95.22% | +0.00 pp | 74.4 min | passed |
| gpqa | 59/90 | 65.56% | 56.67% | +8.89 pp | 31.4 min | passed |
| math500 | 124/125 | 99.20% | 98.40% | +0.80 pp | 44.2 min | passed |
| mmlu | 436/550 | 79.27% | 80.00% | -0.73 pp | 60.3 min | passed |

Formal wall including final audits: 5.60 hours.
Phase wall includes loading/concurrent generation but excludes final audits. Overlapping case durations are not summed.

## Completion and paired outcomes

| Dataset | Missing answers: previous → current | Forced closures | Forced with answer | Previous open cases → answered / correct | Paired wins / losses |
|---|---:|---:|---:|---:|---:|
| aime25 | 0 → 1 | 7 | 6 | 0 → 0 / 0 | 1 / 4 |
| hmmt25 | 1 → 1 | 5 | 4 | 0 → 0 / 0 | 1 / 3 |
| gsm8k | 0 → 0 | 0 | 0 | 0 → 0 / 0 | 12 / 12 |
| gpqa | 6 → 2 | 0 | 0 | 0 → 0 / 0 | 12 / 4 |
| math500 | 0 → 0 | 0 | 0 | 1 → 1 / 1 | 2 / 1 |
| mmlu | 2 → 2 | 0 | 0 | 0 → 0 / 0 | 16 / 20 |

## Method and verification

The only new factor is experiment.memory_quality_gate.max_score_gap = 0.1. An unchosen rollout enters cosine filtering only if both it and the chosen rollout pass existing lookahead eligibility, and its unpenalized continuation mean log probability is no more than 0.1 nats/token below the chosen rollout. Forced first-token likelihood and the lexical doubt penalty are excluded from memory-quality scores.
Quality filtering precedes cosine deduplication: a rejected lower-quality rollout cannot suppress a qualifying alternative. The selected rollout still commits verbatim. The selection rule, its doubt penalty, cosine band and memory framing/compaction are unchanged.
The prior 30,720/2,047 answer reservation and 24,576 branch cap remain unchanged, as do prompts, scorer, model, precision, sampling, seeds and total 32,768 body-token limit. The new option applies only to filtered_futures; checkpoint regressions cover AR and all non-Ours ablation arms, absent/null controls, audit tampering, resume and interaction with closure.
172 CPU tests, lint/format checks and a separate 4-case GPU preflight passed before the study. All four preflight answers were extracted and correct, all four worker audits passed, and the quality gate both accepted and rejected candidates. These cases do not enlarge the official sample count.
All 2,139 canonical IDs and all 24 worker audits passed. completion-proof.json records IDs and report/status hashes. comparison-vs-previous-ours.json records paired wins/losses and closure outcomes.
The 0.1 quality threshold was fixed before this evaluation, using the existing lookahead margin as a scale; no official-set hyperparameter search or answer-based routing was used. All cases, including wrong/missing/capped answers, remain in the denominator.
An inserted thinking-end token is not proof of solving a problem. Extracted answers and correctness are reported separately from natural versus forced closure.
This is one seed and a fixed subset. Confidence is not a correctness verifier. GPU batching can introduce numerical differences between runs. Paired gains/losses do not establish statistical significance or universal improvement. No task-specific or answer-based gate was selected after evaluation.
The context-distraction hypothesis is motivated by https://arxiv.org/abs/2302.00093; that paper does not establish this gate's efficacy for this model or these benchmarks. Earlier results remain immutable.

## Memory filtering observed

| Dataset | Alternative rollouts | Quality accepted | Quality rejected | Cosine retained | Memory injections |
|---|---:|---:|---:|---:|---:|
| aime25 | 1965 | 1633 | 332 | 762 | 762 |
| hmmt25 | 1867 | 1516 | 351 | 788 | 788 |
| gsm8k | 6934 | 5664 | 1270 | 1960 | 1960 |
| gpqa | 2404 | 1788 | 616 | 1096 | 1096 |
| math500 | 2477 | 2064 | 413 | 979 | 979 |
| mmlu | 5271 | 3979 | 1292 | 2293 | 2293 |

## Existing AR reference (different hardware)

This reuses recorded AR measurements only for descriptive analysis; no new AR inference was launched.
AR: 8 RTX PRO 6000 Blackwell GPUs, batch 8, full-v1. Ours: 4 L40S GPUs, AIME/HMMT batch 4 and others 8, l40s-2h-v1.
Only the exact canonical L40S IDs are selected from the existing full AR outcomes. Model/revision, seed, backend, precision, scorer and evaluation-settings hashes match. Hardware and some batches differ, so these deltas are not a matched L40S causal comparison.
AR source: `changho-full-baseline-2026-11-15` / `204b01c7ee62027115be4d5456bb49acc5d382ed`; reference SHA256 `389533293df13ae4eba7c5457dc105cd207768bfddf73ffa6db733f146badb1c`.

| Dataset | n | Existing AR correct | Existing AR accuracy | New Ours accuracy | Reference delta |
|---|---:|---:|---:|---:|---:|
| aime25 | 30 | 21 | 70.00% | 73.33% | +3.33 pp |
| hmmt25 | 25 | 12 | 48.00% | 48.00% | +0.00 pp |
| gsm8k | 1319 | 1258 | 95.38% | 95.22% | -0.15 pp |
| gpqa | 90 | 55 | 61.11% | 65.56% | +4.44 pp |
| math500 | 125 | 123 | 98.40% | 99.20% | +0.80 pp |
| mmlu | 550 | 437 | 79.45% | 79.27% | -0.18 pp |

All six strictly improved vs latest Ours: **False**.
All six strictly above existing cross-hardware AR reference: **False**.
