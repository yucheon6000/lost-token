# Blended memory on the fixed 180-question development sample

**Blended Ours scored 141/180 (78.33%). Previous weighted Ours scored 143/180 (79.44%).**

| Dataset | Previous weighted Ours | Blended Ours | Wins / losses | Original AR reference |
|---|---:|---:|---:|---:|
| aime25 | 24/30 | 23/30 | 1 / 2 | 21/30 |
| hmmt25 | 18/30 | 16/30 | 3 / 5 | 15/30 |
| gsm8k | 29/30 | 29/30 | 0 / 0 | 29/30 |
| gpqa | 19/30 | 20/30 | 3 / 2 | 18/30 |
| math500 | 30/30 | 29/30 | 0 / 1 | 29/30 |
| mmlu | 23/30 | 24/30 | 1 / 0 | 25/30 |
| **Total** | **143/180** | **141/180** | **8 / 10** | **137/180** |

The frozen IDs include all 30 AIME25, all 30 HMMT25, and the preceding 30 each from GSM8K, GPQA Main, MATH500 and MMLU. The primary comparison uses earlier audited Ours outputs on the same IDs, model, seed, per-GPU batch settings and scorer. The blended run used three L40S GPUs (1–3) and the earlier run used four (0–3). This changes worker assignments and batching, so differences are descriptive and may include execution effects. The AR reference was measured on PRO 6000 hardware.

The two groups ran on three L40S GPUs in 167.0 minutes including native audits. All 6 native worker audits passed. The unextractable answer count was 3 versus 5 previously. 182 of 2,630 memory insertions exceeded the old gap limit at their recorded prefixes. That count measures the gate's behavior at a fixed prefix.

See [the method](method.md), [study plan](study-plan.json), [paired outcomes](paired-outcomes.json), [scored preflight](preflight.json), and [audit evidence](completion-proof.json). The formal L40S benchmark uses a different, registered cohort.
