# Evaluation results

| Dataset | Baseline accuracy | Ours accuracy | Change | Baseline time | Ours time |
|---|---:|---:|---:|---:|---:|
| AIME25 | 80.00% (24/30) | 83.33% (25/30) | +3.33 pp | 26m 08s | 45m 39s |
| HMMT25 | 60.00% (18/30) | 46.67% (14/30) | -13.33 pp | 25m 08s | 41m 09s |
| GPQA Main | 55.36% (248/448) | 54.69% (245/448) | -0.67 pp | 1h 43m 27s | 2h 21m 45s |
| MATH500 | 97.00% (485/500) | 97.40% (487/500) | +0.40 pp | 1h 32m 57s | 2h 23m 00s |
| MMLU | 80.94% (11,366/14,042)* | Not run | — | 48h 48m 54s | — |
| GSM8K | 95.53% (1,260/1,319)* | Not run | — | 53m 43s | — |

Change is ours minus baseline, in percentage points. Scores include correct/total questions.
*MMLU and GSM8K baseline scores are from earlier settings; comparable reruns are pending.
MMLU time includes pauses and a change from eight GPUs to four. Other times exclude final audits.

Model: Qwen3-4B-Thinking-2507. All completed runs passed audits.
