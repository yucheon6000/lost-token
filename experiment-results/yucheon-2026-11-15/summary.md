# Yucheon: improved Ours evaluation

**Ours only. AR baseline was neither measured nor reused in this study, as explicitly requested.**
No matched-baseline delta, paired wins/losses, or improvement claim is reported.

Code: `yucheon-2026-11-15` / `0e7fa67be2a776f312af8fe552e70b3906e5e34b`.
Original method commit: `0a7d8a29b8cee89295ba5ca30f85a0e26ba91384`; evaluated source includes the exact late-branch boundary fix and explicit unmeasured-AR reporting.
Cohort: `l40s-2h-v1` / `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`.
Hardware: 4 NVIDIA L40S GPUs; independent models, TP=1, BF16, vLLM 0.10.2 V0.

| Dataset | Correct / n | Accuracy | Batch / GPU | Phase wall | Audit |
|---|---:|---:|---:|---:|---|
| aime25 | 21/30 | 70.00% | 4 | 55.2 min | passed |
| hmmt25 | 13/25 | 52.00% | 4 | 54.7 min | passed |
| gsm8k | 1258/1319 | 95.38% | 8 | 74.4 min | passed |
| gpqa | 51/90 | 56.67% | 8 | 32.9 min | passed |
| math500 | 123/125 | 98.40% | 8 | 51.5 min | passed |
| mmlu | 440/550 | 80.00% | 8 | 60.8 min | passed |

Phase wall includes model loading and concurrent case processing; final audits are excluded from that column. Case elapsed times overlap and are not summed as GPU time.
Formal end-to-end wall including audits: 5.73 hours.

## Evaluated method

- Lookahead uses continuation mean log probability, margin 0.1 and at least 16 continuation tokens.
- A 0.25 penalty is applied for the implemented doubt keywords; this is a keyword heuristic, not a semantic proof of contradiction.
- Alternative rollout memory is retained only in the cosine band [0.2, 0.85) relative to the selected rollout.
- No new fork starts at or beyond body position 24,576. A rollout selected before the boundary is committed verbatim.
- The unverified-memory preamble asks the model to verify constraints and avoid assuming integer answers unless stated.
- Other pinned generation/scoring conditions and all canonical question IDs are unchanged.

## Verification and limitations

154 CPU tests and the source CI passed before this evaluation. The separate 4-case GSM8K GPU preflight produced 4 extracted answers, 4 correct and all worker audits passed. Preflight cases are not added to the official sample count.
All 2139 official cases completed with the original 32,768 body-token cap; capped/open-thinking cases are retained in accuracy, not discarded.
All task/worker audits passed. Frozen case IDs and report hashes are recorded in completion-proof.json.
This is a single-seed, fixed-subset evaluation of a bundled method. It does not isolate individual component effects or establish statistical significance.
Existing PRO 6000/full-v1 baseline results were not relabeled as a matched L40S baseline.
The former two-hour sizing forecasts are planning estimates; the table above contains measured phase times.
