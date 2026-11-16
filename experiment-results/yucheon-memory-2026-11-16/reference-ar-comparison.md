# Existing AR: exact-ID reference comparison

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
