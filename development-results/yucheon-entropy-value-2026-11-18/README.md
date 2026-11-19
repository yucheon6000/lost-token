# Entropy-guided arithmetic re-sampling on L40S

All six datasets use the registered l40s-2h-v1 IDs. Each task ran on one L40S, and independent tasks used available GPUs concurrently. This is a development result with its actual allocation recorded in environment.json.

Existing AR is a descriptive PRO 6000 reference on the same IDs. Previous L40S Ours is the earlier quality-memory method, which also differs in rollout scoring, memory selection and task sharding.

| Dataset | n | Entropy Ours | Prior L40S Ours | Existing PRO AR | Probed | Changed | Phase wall (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| aime25 | 30 | 23 | 22 | 21 | 5 | 0 | 8753.2 |
| gpqa | 90 | 49 | 59 | 55 | 3 | 0 | 6849.3 |
| gsm8k | 1319 | 1255 | 1256 | 1258 | 1 | 0 | 16559.6 |
| hmmt25 | 25 | 12 | 12 | 12 | 2 | 0 | 8888.0 |
| math500 | 125 | 124 | 124 | 123 | 2 | 0 | 7270.4 |
| mmlu | 550 | 442 | 436 | 437 | 2 | 0 | 13011.0 |
| **Total** | 2139 | 1905 | 1909 | 1906 | 15 | 0 | — |

Changed counts verified rollout replacements. Final-answer wins and losses against the recorded comparators are in comparison-details.json.

AR reference commit: 204b01c7ee62027115be4d5456bb49acc5d382ed. Reference SHA256: 389533293df13ae4eba7c5457dc105cd207768bfddf73ffa6db733f146badb1c.
