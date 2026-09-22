# Method and implementation contract

Lost Tokens reuses **unchosen reasoning branches as in-context memory**, without
training or changing model weights. The implementation is based on the recurrent
reasoning-memory protocol used in the project's experiments.

1. Generate normally inside the model's reasoning region. Require at least one
   generated reasoning token and the configured minimum distance from the last
   branch point. Never intervene in the final-answer region.
2. At an eligible position, include all non-special tokens whose raw next-token
   probability is at least 0.20. Require at least two candidates. If the most
   probable token is special, do not fork. This is independent of the sampling
   top-k/top-p filter.
3. Clone the same parent KV state independently for each candidate, force its
   first token, and continue for at most 32 tokens including that first token.
   Stop at EOS or the reasoning-end marker. Seeds are derived from the case,
   position and candidate identity; checkpoint segment boundaries do not change
   token sampling.
4. Select the highest-probability candidate. Embed only the rollout texts with
   Qwen3-Embedding-0.6B. Greedily discard alternatives whose cosine similarity is
   at least 0.85 to the selected branch or an already retained alternative.
5. Insert retained **unchosen** rollout text inside a `<possibilities>` block.
   Then commit the selected rollout's exact generated tokens. Memory is a set of
   unverified possibilities, not a collection of independent confirmations.
6. Continue and repeat. The default minimum branch interval is 256 generated body
   tokens; injected memory does not count toward that interval or the generation
   cap. There is no fixed maximum event count.

The memory capacity is 8,192 tokens, with compaction down to 4,096 and a maximum
2,048-token insertion per event. Compaction removes complete old memory blocks;
it preserves all generated body tokens. A generated-token repetition guard is
applied consistently and recorded in the ledger.

For long roots, the exact-dtype parent cache temporarily moves to CPU while a
candidate has its own independent GPU cache. This changes data movement, not
model precision, candidate tokens or inference logic. The default offload
threshold is 49,000 tokens. Actual capacity depends on the GPU, model, and config.

## Evaluation semantics

`baseline` maps to `plain_ar`; `ours` maps to `filtered_futures`. Both use the
same prompts, per-case seed, temperature 0.6, top-p 0.95, top-k 20 and output cap.
Answers are extracted only after the reasoning-end marker (or a completed EOS
response). A capped, unclosed scratchpad is not treated as a final answer.
Math tasks require an explicit boxed final answer, scored with locked Math-Verify;
multiple-choice tasks require an explicit final-answer letter.

This comparison changes both alternative memory and selected-rollout commit.
It is not a memory-only causal ablation. The selected continuation has been
generated before the memory insertion and is committed verbatim afterwards.
Larger rollouts therefore change more than the content of alternative memory.

## Reproducibility and provenance

- Raw source revisions and SHA256 values are pinned; input adapters are hash-bound
  to prepared rows. Answer fields are never appended to model prompts.
- Worker identities freeze configuration, normalized split, source files, runtime
  packages, device information, and the original time schedule.
- Every completed inference call has an atomic, content-addressed checkpoint.
  Recovery reconstructs the prefix and reuses saved calls without resampling.
  A partly executed call restarts from the last completed checkpoint.
- Audits reconstruct generated and injected tokens, candidate roots, committed
  continuations, cosine decisions, repetition guards, final scoring, and cost sums.
- Equal time budgets do not imply equal completed question sets. Reports show
  own completed counts and paired accuracy on the common completed set. Completion
  selection, unequal benchmark sizes, one seed and numerical nondeterminism limit
  what those scores establish.

The historical machine-specific launch scripts are intentionally absent. The
portable CLI uses the same inference algorithm with configurable storage, devices,
dataset subsets and time budgets. Historical predictions and checkpoint directories
are preserved outside the public repository.
