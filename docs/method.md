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

## Budget forcing entropy gating and sentence boundaries

`configs/bounded-entropy-sentence.json` enables three additions while the packaged
defaults retain the original behavior. All original candidate, memory, and commit
rules above still apply.

Before step 2, compute Shannon entropy over the full raw next-token distribution,
`H = -sum(p * log(p))`, using natural logarithms. Require `H >= 0.65` nats as well
as at least two ordinary candidates with probability at least 0.20. The entropy
threshold is `experiment.min_branch_entropy`; absent or `null` disables it.
No numerical-token exceptions, probability-ratio fallback, or task-specific gates
are added.

In step 3, `experiment.rollout_early_stop` sets the minimum rollout length and
boundary strings. The combined method uses 13 tokens and `.\n`, `.\t`, `. `,
`\n\n`, `\n-`, and `\n*`. Only a boundary newly completed at or after the minimum
length stops the rollout; a boundary emitted earlier is not reused. Detection
uses decoded rollout prefixes so a boundary can span tokenizer pieces. EOS and
reasoning-end markers remain immediate stops. The main continuation is unaffected
by these boundary rules. There is no entropy-dependent rollout-length adjustment.

Before generating or exploring another thinking token, enforce the body budget.
`experiment.budget_forcing` reserves a position for a forced `</think>` and a
maximum number of answer tokens. Each main segment and candidate rollout is
limited by the remaining thinking budget. At body position 31,743, an open
thinking trace receives one persisted `</think>` token, leaving 1,024 answer
tokens within a total of 32,768. If reasoning closes naturally first, no forced
token is inserted and generation continues under the original body cap. The rule
supports all four arms; final-answer generation never branches.

The 32K limit counts generated body tokens, including committed selected-rollout
tokens and the forced marker. Input, injected memory, and unchosen speculative
tokens have separate budgets. This is not a 32K cap on total model work or context.
Budget forcing guarantees a transition out of an open thinking trace and bounded
generation; final-answer completeness and accuracy remain model outcomes.

The atomic ledger records the same parent states, truncated rollout requests,
forced boundary, exact commits, and per-position seeds on interruption and
resume. Audit verifies the entropy requirement, each valid early stop, and the
forcing position in addition to the original invariants.

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
