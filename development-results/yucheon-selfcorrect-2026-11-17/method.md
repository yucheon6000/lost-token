# Method: allow self-correction language

Code branch: `yucheon-selfcorrect-2026-11-17`; immutable execution commit: `9feae0c947e5c4fa3ea1b0bee2bd675b50019c0d`.

Only `experiment.lookahead.contradiction_penalty` changes from **0.25 to 0.0**, in `configs/vllm-ours-selfcorrect.json`. All inference implementation files and scoring code remain byte-identical to the evaluated quality-memory method at `2c8b4870afab764f51cf5092467add4a3832f801`.

The removed penalty is triggered by a substring match on `wait,`, `wait.`, `hold on`, `contradiction`, `impossible`, or `mistake`. The hypothesis is that these words can describe useful self-correction or valid contradiction reasoning, so a blanket score penalty may reject productive continuations. This hypothesis was fixed before this pilot; fixed-prefix replay changes 186 of 1,989 historical choices, which is not an accuracy result.

Preserved: two token candidates, probability threshold 0.20, at most 64 tokens per candidate, mean continuation log probability excluding the forced first token, selection margin 0.10, minimum continuation length and terminal checks, independent candidate contexts, verbatim selected-rollout commit, memory-quality cutoff 0.10, cosine filtering, memory compaction, repetition guard, seed, model/tokenizer revisions, 32,768 output tokens, and the existing answer reservation.

The control uses `configs/vllm-ours-quality-memory.json`. The candidate uses the new config. Both are native `--arms ours` executions, run in parallel on two L40S GPUs each. The four-device machine is fully allocated, while each paired variant receives an equal two-device allocation. Short tasks use batch maximum 8 and AIME/HMMT maximum 4. These are development allocations, not a new canonical hardware profile.

The frozen 60 IDs were selected independently of labels for the preceding consistency diagnostic and reused here. This is now development data, not a held-out confirmation set. Gold answers are used only for scoring. Dynamic batching and cache execution can still vary between methods; one small pilot does not isolate every numerical effect or demonstrate universal improvement. The canonical cohorts and accuracy index are unchanged.
