# Ours with a reserved final-answer budget

Only Ours was executed, following the user's standing instruction. AR was neither executed nor reused.
All deltas below compare against the previous Ours, not an AR baseline.

Code: `yucheon-2026-11-16` / `2309ee4da32203ae0ca2b741907029c2f9c81d9d`.
Previous Ours: `yucheon-2026-11-15` / `0e7fa67be2a776f312af8fe552e70b3906e5e34b`.
Hardware: 4 NVIDIA L40S, independent TP=1 workers, BF16, vLLM 0.10.2 V0.
Cohort: `l40s-2h-v1` / `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`.

| Dataset | Correct / n | Accuracy | Previous Ours | Delta vs previous Ours | Phase wall | Audit |
|---|---:|---:|---:|---:|---:|---|
| aime25 | 25/30 | 83.33% | 70.00% | +13.33 pp | 53.7 min | passed |
| hmmt25 | 14/25 | 56.00% | 52.00% | +4.00 pp | 43.9 min | passed |
| gsm8k | 1256/1319 | 95.22% | 95.38% | -0.15 pp | 74.9 min | passed |
| gpqa | 51/90 | 56.67% | 56.67% | +0.00 pp | 31.7 min | passed |
| math500 | 123/125 | 98.40% | 98.40% | +0.00 pp | 51.5 min | passed |
| mmlu | 440/550 | 80.00% | 80.00% | +0.00 pp | 59.1 min | passed |

Formal wall including final audits: 5.48 hours.
Phase wall includes loading/concurrent generation but excludes final audits. Overlapping case durations are not summed.

## Completion and paired outcomes

| Dataset | Missing answers: previous → current | Forced closures | Forced with answer | Previous open cases → answered / correct | Paired wins / losses |
|---|---:|---:|---:|---:|---:|
| aime25 | 6 → 0 | 4 | 4 | 6 → 6 / 4 | 4 / 0 |
| hmmt25 | 5 → 1 | 5 | 4 | 5 → 4 / 1 | 2 / 1 |
| gsm8k | 0 → 0 | 0 | 0 | 0 → 0 / 0 | 9 / 11 |
| gpqa | 6 → 6 | 0 | 0 | 0 → 0 / 0 | 8 / 8 |
| math500 | 0 → 0 | 1 | 1 | 0 → 0 / 0 | 1 / 1 |
| mmlu | 2 → 2 | 0 | 0 | 0 → 0 / 0 | 18 / 18 |

## Method and verification

The sole method change is experiment.ours_budget_forcing: at body position 30,720, if thinking remains open, commit one thinking-end token and allow up to 2,047 final-answer tokens. Total body cap remains 32,768. Natural earlier endings are untouched.
The existing fork cap stays 24,576; validation ensures every full selected rollout can finish before the closure boundary. Lookahead, doubt penalty, cosine band, memory framing/compaction, prompt, scorer, model, sampling and seeds are unchanged.
The new option applies only to filtered_futures. AR and all_futures checkpoint regressions passed; the other ablation arms also do not receive this policy. Existing AR-only budget_forcing remains separate.
161 CPU tests, lint/format checks, a forced-path 4-case GPU preflight and a separate formal-config 4-case GPU preflight passed before the study. Preflight cases do not enlarge the official sample count.
All 2,139 canonical IDs and all 24 worker audits passed. completion-proof.json records IDs and report/status hashes. comparison-vs-previous-ours.json records paired wins/losses and closure outcomes.
The 30,720 threshold was selected before this evaluation; no official-set parameter search was used. All cases, including wrong/missing/capped answers, remain in the denominator.
An inserted thinking-end token is not proof of solving a problem. Extracted answers and correctness are reported separately from natural versus forced closure.
This is one seed and a fixed subset. GPU batching can introduce numerical differences between runs; changes on cases that never trigger closure are not evidence of a closure benefit. Paired gains/losses do not establish statistical significance.
Existing AR scores were not relabeled or borrowed across profiles. The earlier Ours result remains immutable.
