# Whole-suite single-stream disagreement verification

Required benchmarks: AIME25 30, HMMT25 30, GPQA Main 448, GSM8K 1319, MATH500 500, MMLU 14042. Every ID comes verbatim from the committed full-v1 manifest; prepared rows and stored hashes were verified. The canonical shared subsets remain unchanged. Full scope is explicitly required by the user. The controller refuses a missing full manifest or a truncated required suite.

Identical generation method/configs/source to the prior completed disagreement study: one continuing solution, existing short speculative candidates, exact selected rollout commit, at most eight local checks of up to 192 body tokens, checks after body position 512 and spaced by 1024 body tokens, 32768 total body cap. No completed-answer voting, reranking or best-of-N. All speculation/cue/check input and output costs are accounted for; same body cap is not equal FLOPs.

Argmax for AIME/HMMT/GSM8K and lookahead for GPQA/MATH500/MMLU, selected from the historical configurations before the new missing-set results. The fresh policy-off control differs only in the verification intervention. No benchmark gold enters inference or verification.

AIME/HMMT/GPQA treatment and control conditions were already fully evaluated and audited. They are reused only after exact package source, GPU allocation, configuration, ID coverage, outcome hash and audit checks. Original completion dates, code commit and wall time are retained; no old computation is represented as newly run. All six missing GSM8K/MATH500/MMLU conditions are queued for fresh generation. Historical ensemble results are not used.

Execution uses eight allocated RTX PRO 6000 Blackwell GPUs, vLLM TP=1 with up to eight concurrent cases per GPU, pinned Qwen3-4B-Thinking-2507 BF16 and unchanged seed 95021. See environment.json for UUIDs, driver/CUDA, exact packages and storage-independent settings. Decoder source is byte-identical to the audited 16-case GPU preflight (all final answers extracted and all eight worker audits passed). This extension changes orchestration and cohort validation only. Full CPU suite: 177 tests passed. Prepare was also verified from /tmp. Runtime source/configs are frozen while any condition is running; normal resume retains original checkpoints and schedules.

Code branch follows actual completion date in Asia/Seoul. Partial/failed conditions remain explicit. Primary comparison is against the frozen single-pass AR; fresh control and historical ours are additionally reported. Single-seed benchmark development results and dynamic GPU batching do not establish reliable generalization. Results from all six benchmarks must be reported regardless of regressions.

Execution branch: `changho-disagreement-full-2026-11-20`; code commit: `fd28c1438fb4e0d31465ff65b33a288185ce5008`. Whole-suite completion: 2026-11-20T18:03:07.761564+09:00. Reused conditions retain original commit a24f8e212cba4ec90b5ce82057c64153aa872f6b and their original completion timestamps.
