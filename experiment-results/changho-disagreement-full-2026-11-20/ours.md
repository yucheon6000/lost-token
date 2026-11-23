# Single-stream local verification: final full-suite results

All six datasets are complete at their original full sizes. All 12 treatment/control conditions passed worker audits. The three previously completed AIME25/HMMT25/GPQA conditions retain their original audited provenance; the missing GSM8K/MATH500/MMLU conditions were generated on eight GPUs between 2026-11-20 01:25 and 18:03 KST (16 h 37 min elapsed). No completed-answer ensemble, voting or best-of-N selection is used.

| Full dataset | n | Frozen single-pass AR | Fresh policy-off control | Local verification | Δ correct vs AR | Δ correct vs control |
|---|---:|---:|---:|---:|---:|---:|
| aime25 | 30 | 21/30 (70.00%) | 23/30 (76.67%) | 20/30 (66.67%) | -1 | -3 |
| hmmt25 | 30 | 15/30 (50.00%) | 15/30 (50.00%) | 16/30 (53.33%) | +1 | +1 |
| gpqa | 448 | 275/448 (61.38%) | 279/448 (62.28%) | 283/448 (63.17%) | +8 | +4 |
| gsm8k | 1319 | 1258/1319 (95.38%) | 1260/1319 (95.53%) | 1252/1319 (94.92%) | -6 | -8 |
| math500 | 500 | 489/500 (97.80%) | 493/500 (98.60%) | 489/500 (97.80%) | +0 | -4 |
| mmlu | 14042 | 11438/14042 (81.46%) | 11435/14042 (81.43%) | 11427/14042 (81.38%) | -11 | -8 |

Decision: reject this verification configuration as a general improvement. Versus frozen single-pass AR it wins on HMMT/GPQA, ties on MATH500 and loses on AIME/GSM8K/MMLU. The verification intervention also loses to its fresh policy-off control on four of six benchmarks. GPQA equals the earlier best single-pass ours (283/448). Single-seed development on previously inspected benchmarks and dynamic-batch numerical variation do not establish reliable generalization or statistical significance.

Verification is performed on the SAME continuing stream, with short independent speculative candidates inherited from the existing method. Up to eight checks of at most 192 body tokens consume the original 32768-token cap. Speculation, side-input prefill and verification costs are recorded; equal body caps do not imply equal compute. The mathematical/constraint checks are model-generated and are not externally certified. No benchmark reference answer enters inference or verification.

## Recorded cost versus control

| Dataset | Verification phase / control phase (min) | Protocol forward-token estimate overhead |
|---|---:|---:|
| aime25 | 18.5 / 17.5 | +14.55% |
| hmmt25 | 18.5 / 18.0 | +18.63% |
| gpqa | 42.3 / 40.5 | +1.45% |
| gsm8k | 22.8 / 21.0 | +8.27% |
| math500 | 43.5 / 42.3 | +7.36% |
| mmlu | 382.5 / 363.9 | +3.74% |

Phase wall times are the original generation phases; total controller elapsed also includes initialization, auditing and reporting. Protocol token/attention counts are accounting estimates, not measured FLOPs. Concurrent per-case seconds must not be summed and presented as wall time.

Code: `changho-disagreement-full-2026-11-20`, commit `fd28c1438fb4e0d31465ff65b33a288185ce5008`. Reused conditions originate at commit `a24f8e212cba4ec90b5ce82057c64153aa872f6b`. Completion date remains 2026-11-20 even though this report was generated later. Decoder source and frozen runtime settings were preserved throughout both runs.

[Baseline](baseline.md) · [Method](method.md) · [Environment](environment.json) · [Detailed execution table](results.md)
