# Method: unchanged weighted Ours

Source branch `yucheon-weighted-2026-11-17`, immutable execution commit `fe06f6db1f0ce3c053c9da24b54e3e6c4080feea`.

The implementation is unchanged from the preceding weighted pilot. Selection alone weights the continuation first-half mean log probability by 0.25 and second-half mean by 0.75, excluding the forced first token. The memory quality gate retains uniform continuation means. The 0.10 switching margin, two candidates, up-to-64-token previews, frozen generator/embedding models, exact rollout commit, memory compaction, 32K body budget, answer reservation, sampling, prompts, adapters and scorer remain unchanged.

Only evaluation scope and GPU allocation change: full 30-question AIME25 and HMMT25, nested 30-question samples for the other four tasks, four L40S GPUs for each task group, batch maxima 4 for math and 8 for the others. Each case is rerun rather than importing old inference checkpoints. The frozen IDs and source/config hashes are in [study-plan.json](study-plan.json) and [sample-manifest.json](sample-manifest.json).

Only weighted Ours runs. AR is reused from the original PRO 6000 reference and labeled cross-hardware context. There is no fresh matched 180-question uniform control, and this expanded development evaluation is not a full registered L40S submission. No accuracy improvement is inferred solely from a larger sample, resource use or historical overlap.
