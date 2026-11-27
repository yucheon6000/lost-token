# Same selected three seeds: all six full benchmarks

Seeds: 95021, 95022, 95023
Post-hoc selection on five non-MMLU benchmarks; fixed before the missing MMLU seed was generated. No MMLU-based reselection.

| Dataset | Baseline | Ours argmax | Delta (pp) |
|---|---:|---:|---:|
| aime25 | 65.56 (59/90) | 77.78 (70/90) | +12.22 |
| hmmt25 | 51.11 (46/90) | 56.67 (51/90) | +5.56 |
| gpqa | 61.31 (824/1,344) | 61.61 (828/1,344) | +0.30 |
| gsm8k | 95.12 (3,764/3,957) | 95.27 (3,770/3,957) | +0.15 |
| math500 | 97.93 (1,469/1,500) | 98.13 (1,472/1,500) | +0.20 |
| mmlu | 81.35 (34,269/42,126) | 81.49 (34,328/42,126) | +0.14 |

Denominators are repeated evaluations per arm across the same three seeds. The complete original five-seed report and excluded seed results remain unchanged.
