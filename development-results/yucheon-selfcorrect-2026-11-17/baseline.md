# Reused AR reference

No AR baseline inference was run for this pilot. The original frozen reference is reused unchanged.

- Reference SHA256: `389533293df13ae4eba7c5457dc105cd207768bfddf73ffa6db733f146badb1c`.
- Original branch: `changho-2026-11-15`.
- Original commit: `204b01c7ee62027115be4d5456bb49acc5d382ed`.
- Original hardware: PRO 6000 full-cohort reference. The selected-ID scores below are cross-hardware context, not a matched L40S baseline.
- The primary accuracy comparison in this pilot is a fresh current-Ours control against the modified Ours, on matching L40S allocations.

| Dataset | Reused AR correct on the 10 selected IDs |
|---|---:|
| aime25 | 7/10 |
| gpqa | 6/10 |
| gsm8k | 10/10 |
| hmmt25 | 4/10 |
| math500 | 10/10 |
| mmlu | 8/10 |

Reference: [original baseline-reference.json](../../experiment-results/changho-full-baseline-2026-11-15/baseline-reference.json). The source reference and its original timing/provenance remain unchanged.
