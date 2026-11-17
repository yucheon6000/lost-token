# Reused frozen AR reference

No AR inference was run. The unchanged full-cohort reference is reused on exactly the selected IDs as cross-hardware context, not a matched L40S baseline.

- Payload SHA256: `389533293df13ae4eba7c5457dc105cd207768bfddf73ffa6db733f146badb1c`.
- File SHA256: `b3e493a958e9311bacf40570f49583e0b386d1668b8f1cf599717342cfe9907a`.
- Original code branch: `changho-2026-11-15`.
- Original code commit: `204b01c7ee62027115be4d5456bb49acc5d382ed`.
- Original hardware: 8 RTX PRO 6000 GPUs. Original full reference, timing and provenance are preserved in [the original submission](../../experiment-results/changho-full-baseline-2026-11-15/baseline-reference.json).

| Dataset | Frozen AR correct on the same selected 30 IDs |
|---|---:|
| aime25 | 21/30 |
| hmmt25 | 15/30 |
| gsm8k | 29/30 |
| gpqa | 18/30 |
| math500 | 29/30 |
| mmlu | 25/30 |

Total selected-ID AR score: 137/180. These cross-hardware values do not establish a weighting effect. All pairs: [paired-outcomes.json](paired-outcomes.json).
