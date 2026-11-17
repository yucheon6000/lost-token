# Method: emphasize later continuation confidence

Code branch: `yucheon-weighted-2026-11-17`; execution commit: `fe06f6db1f0ce3c053c9da24b54e3e6c4080feea`. Parent method: `yucheon-selfcorrect-2026-11-17` / `9feae0c947e5c4fa3ea1b0bee2bd675b50019c0d`.

The only configured intervention is `lookahead.half_weights: [0.25, 0.75]`, added to the self-correction config. The forced first candidate token is excluded. For a full 64-token preview, selection uses:

```text
score = 0.25 * mean(logp of preview tokens 2–32)
      + 0.75 * mean(logp of preview tokens 33–64)
```

For n actual continuation tokens, split after floor(n/2). Existing minimum-length, terminal and blank-text eligibility checks are unchanged. An empty continuation has no score; a sole continuation retains its one-token score and cannot meet the actual 16-token minimum. The control retains the original uniform mean over all continuation tokens; because there are 63 after excluding the first token, that is not exactly a 50/50 average of half means.

The 0.10 switching margin and disabled lexical penalty remain unchanged. The memory quality gate deliberately uses its original **uniform** mean log probability, not the weighted selection score, with the same 0.10 score-gap cutoff. The actual chosen rank can change, which naturally changes which unchosen rollout is considered for memory. The gate rule itself is held fixed.

Preserved: frozen model and tokenizer revisions, two token candidates, up-to-64-token previews, reasoning-only forks, independent candidate caches, verbatim selected rollout commit, cosine gate, memory capacity/compaction, sampling seeds, 32,768 output tokens, answer reservation, prompt/data adapters, and scorer. No verifier, additional model calls, output normalization, or answer-format changes were added. Existing configs without half_weights retain their original scores and checkpoint fields; default golden and replay tests check this.

Hypothesis: weighting later continuation confidence may reject branches whose apparent advantage comes from an easy opening. This remains a confidence heuristic and does not establish correctness. The feature is evaluated by final-answer accuracy, not resource savings.

Both variants run fresh, native `--arms ours`, on two L40S GPUs each on the four-device machine. The same fixed 10 questions per dataset are reused. Batches have maximum 8 for the four shorter tasks and 4 for AIME/HMMT. The pilot is development data and does not replace canonical full-cohort IDs or enter the official accuracy index. Dynamic execution paths can still differ.
