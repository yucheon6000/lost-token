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

## Rollouts ending after two sentences

The newer `configs/sparse-sentence-rollouts.json` profile uses an entropy threshold
of 1.0 nats and `experiment.rollout_sentence_ends: 2`, with the prior
`rollout_early_stop` rule absent. These two stopping rules are mutually exclusive.
The rollout's request count becomes its remaining body/thinking budget, rather
than `branch_tokens`. The latter still governs the original token-length mode.
No minimum number of rollout tokens is required.

Each candidate independently counts sentence endings from its forced first token.
The first ending can finish a sentence begun in the shared parent. ASCII terminal
punctuation requires a following whitespace separator, allowing optional closing
quotes/brackets. A punctuation cluster counts once. This avoids counting decimal
points before the next digit arrives; common abbreviations and numbered-list
markers are also excluded. Full-width terminal punctuation needs no separator.
Counting decodes only a bounded recent token window, avoiding repeatedly decoding
an arbitrarily long candidate prefix. The window is an implementation detail and
does not cap generation length.

Each candidate records its `sentence_ends` count. Audit recomputes each increment
from the saved token prefixes and rejects premature stops or tokens after the
target has already been reached. EOS and reasoning-end markers remain immediate
termination conditions. A candidate without two endings can consume at most the
remaining body budget. Timed workers check their original deadline between tokens
so a long candidate cannot delay an arm transition indefinitely. An interrupted
candidate restarts from its last completed parent checkpoint; completed calls
are replayed unchanged.

The memory encoder's configured input limit and the event-memory reservation
remain separate safeguards. Exceeding either fails explicitly; sentence mode
never silently truncates an alternative to make it fit. Actual accuracy, event
count, and net speed require a new paired evaluation: changing the threshold or
rollout stop changes the subsequent reasoning trajectory.

The sparse profile uses a 4,096-token encoder limit and 8,192-token event memory
reservation after reproducing a failure on a 565-token original preview. Its
14,336-token memory capacity preserves the old 6,144-token compaction trigger
and 4,096-token compaction target. The context guard increases to 79,904 to cover
the enlarged reservation. This extends supported inputs without changing cosine
filtering, truncating text, or changing normal compaction timing.

## Explicit unchosen branch memory

The sparse profile uses `experiment.memory_format: "original_unchosen"`, with
`max_branch_candidates: 2`. Eligibility still uses the complete raw distribution.
Only the two highest probability qualifying candidates are explored at each fork:
the original, always selected under the existing argmax rule, and one unchosen
alternative. The original is the method's selected rollout, not a separate third
branch or a guarantee of matching plain-AR sampling. The reference ablation keeps
its single-preview semantics. Redundant unchosen text can still be filtered out.

The initial user-message instructions define `Unchosen` as an explored but
unselected, unverified alternative, and `Original (chosen)` as the continuation
being followed. Definitions appear once before the problem. Each memory block
then contains `Unchosen:`, the quoted alternative, and `Original (chosen):`.
The latter closes the quote block and identifies the exact selected rollout
committed next as body tokens. Selected text is never duplicated in side memory.
The alternative payload is preserved apart from quotation prefixes and escaped
reasoning or memory control tags.

Formatting takes place after semantic filtering, so the embedding encoder still
receives raw rollout text. Absent/null `memory_format`, or `"possibilities"`, keeps
the original bytes for older profiles; `"unchosen_branches"` retains the longer
per-event explanation. Audit verifies the initial instructions, candidate limit,
reported memory string and encoded token IDs. Repetition/markup diagnostics count
copied labels only for the active format; quoted source lines are not classified
as standalone framing labels.

Preparation includes the definitions in prompt lengths and LongBench context
reservation. Its identity hashes the instructions so primed and unprimed inputs
cannot share an incorrectly sized cache. Runtime branch thresholds and rollout
limits do not affect this prompt identity. A plain-AR arm using the compact
profile receives the same definitions, whereas the original defaults preserve
the unprimed baseline. These controls differ and must be reported explicitly.
Contextual framing does not establish correct interpretation or improved accuracy.

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
