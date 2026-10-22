# GH experiment results and failure analysis

Reviewed on 2026-10-22. This report covers all six run directories currently present under `workspace/outputs/`. Results come from saved run plans, status files, reports, worker configurations, and error logs. Saved audits were inspected, not rerun. Times below are rounded; event timestamps are shown in Korea Standard Time (UTC+9).

## Successful full-dataset runs

All three runs below completed their entire planned dataset, have `state: complete`, and recorded `audits_passed: true`. Each used the `ours` arm on GPUs 0 and 1, without a question limit or time deadline.

| Run | Dataset | Completed | Correct | Incorrect | Accuracy | Evaluation wall time |
|---|---|---:|---:|---:|---:|---:|
| aime25-GH | AIME 2025 | 30/30 | 21 | 9 | 70.00% | 2h 51m 25s |
| hmmt25-GH | HMMT February 2025 | 30/30 | 16 | 14 | 53.33% | 3h 9m 11s |
| gpqa-GH | GPQA Main | 448/448 | 246 | 202 | 54.91% | 12h 22m 23s |

**AIME25:** The method answered 21 of the 30 questions correctly. This is full coverage of this repository's AIME25 dataset, rather than a smoke test or a subset.

**HMMT25:** The method answered 16 of 30 questions correctly. Its accuracy is lower than AIME25 in these runs, but these are different question sets; the difference is not a controlled comparison of method performance.

**GPQA:** The current `gpqa-GH` is a genuine GPQA evaluation: its plan selects `gpqa` and its report contains 448 GPQA outcomes. It was created on October 17 at 04:31 KST and completed on October 17 at 17:00 KST. It is distinct from the earlier mislabeled HMMT run named `gpqa-GH` that was deleted. That deleted run is excluded here.

| Run | Generated body tokens | Branch events | Mean case time | Median case time | Body tokens/second |
|---|---:|---:|---:|---:|---:|
| aime25-GH | 629,516 | 559 | 648.20 s | 647.39 s | 32.37 |
| hmmt25-GH | 693,798 | 616 | 699.75 s | 757.42 s | 33.05 |
| gpqa-GH | 3,709,718 | 3,390 | 195.84 s | 183.72 s | 42.28 |

Evaluation wall time includes model loading but excludes final audits. Case times include generation and auxiliary work but exclude model loading and final audits. Cases run in parallel, so summed case time is not wall time. Body tokens/second is generated body tokens divided by summed case time, not combined two-GPU throughput. Branch events count exploration events, not necessarily retained memory insertions. All completed cases in these three runs recorded `thinking_complete`.

There is **no baseline arm** in these runs. These scores establish observed accuracy for the implemented method, but cannot establish an accuracy improvement or speed advantage over baseline. Audit success establishes that the saved run passed the repository's checks, not that every answer is correct. These are single-seed results.

## Configuration used

The saved worker configurations use the sparse full-feature profile represented by `configs/sparse-sentence-rollouts.json`:

- Generator: Qwen/Qwen3-4B-Thinking-2507; embeddings: Qwen/Qwen3-Embedding-0.6B on CPU.
- Arm: `ours` / `filtered_futures`; seed: 95021.
- Entropy threshold: 1.3 nats; minimum fork interval: 1,024 body tokens; candidate probability threshold: 0.20.
- Up to two candidate continuations; rollouts stop at two recognized sentence endings or other stopping conditions. This sentence mode does not impose the original fixed 32-token rollout cap.
- Cosine threshold: 0.85; comparison against the four most recent retained alternatives.
- `original_unchosen` memory formatting and exact selected-rollout commit.
- Generated body cap: 32,768 tokens; forced reasoning close at body position 30,719, reserving one close token and 2,048 answer tokens.
- Encoder input limit: 4,096 tokens; per-event memory reservation: 8,192 tokens; total memory capacity: 14,336 tokens; compaction target: 4,096 tokens.

## Failed runs: partial results only

These values are from the last saved reports before failure. They are not full-dataset benchmark scores and final run audits did not complete. Coverage stopped at the error, so the completed subset must not be treated as representative of the entire benchmark.

| Run | Last reported completion | Dataset coverage | Correct on completed cases | Partial accuracy | Failure time (KST) |
|---|---:|---:|---:|---:|---|
| mmlu-GH | 715/14,042 | 5.09% | 564/715 | 78.88% | October 18, 11:27 |
| supergpqa-GH | 779/26,529 | 2.94% | 298/779 | 38.25% | October 19, 03:58 |

### What actually failed

Both worker-0 logs end with the same exception:

```text
ValueError: Encoder length exceeded; refusing silent truncation
```

The controller then reported:

```text
RuntimeError: ours-worker0 exited 1; see .../workspace/logs/<run-name>
```

The controller message is the consequence, not the underlying cause. During branch comparison, `compare_rollouts()` calls `encoder.encode()`. The embedding tokenizer uses `truncation=False`. When the tokenized input exceeds the configured 4,096-token limit, the encoder explicitly raises the exception rather than silently changing the text used for similarity scoring.

The two-sentence rollout rule can generate thousands of tokens before finding two recognized sentence endings. Sentence count therefore does not guarantee that a candidate fits the embedding input limit. The observed failure is this configured length guard; these traces do not report a CUDA out-of-memory error.

### MMLU evidence

The failing case was `mmlu-professional_law-11126`. Its last long-rollout progress line recorded **8,535 generated tokens with only one of two sentence endings recognized**, before comparison failed. This is a progress-log observation, not an exact final embedding-token count: generator and encoder tokenization are separate.

The controller's last saved progress was 715 completed cases. The saved report records 712 cases with `thinking_complete`; completion of a scored case and completion of its reasoning phase are separate fields.

### SuperGPQA evidence

The failing case was `supergpqa-5383a1f504814c13a36f308540f2382b`. Candidate rollout progress reached **4,504 and 4,505 generated tokens**, with zero of two sentence endings recognized in those log entries, before the encoder rejected the comparison input. These are logged intermediate generation lengths, not exact final embedding lengths.

The controller's last saved progress was 779 completed cases. Its last remaining-time estimate was about 22 days, but that estimate is stale: a failed run has no active completion ETA.

### Why the other worker stopped, and recovery implications

After worker 0 failed, the controller terminated the other worker during cleanup. Worker 1's `KeyboardInterrupt: signal 15` is a secondary shutdown event, not a separate encoder failure.

Existing checkpoints and reports remain on disk. Resuming with the same deterministic inputs and limits is expected to hit the same oversized comparison again. Editing a saved run's configuration or code would conflict with its identity/provenance checks and must not be used to bypass them.

A future remedy needs a deliberately validated policy: coordinated encoder and memory limits, or explicit handling of oversized rollouts. Merely raising the encoder limit can expose the separate 8,192-token event-memory guard, which raises `Memory reservation too small; refusing to silently drop qualifying candidates`. That second error is a potential subsequent failure, not the error observed in these two runs. Changing rollout length or dropping candidates would change method behavior and must be documented. No such fix or migration was performed for this report.

## LongBench: intentionally paused

`longbench-GH` is `interrupted`, with **0/503 completed questions**. Both workers began their first question before the requested pause on October 18 at 18:12 KST. Its saved exception, `KeyboardInterrupt('signal 15')`, reflects the deliberate graceful stop, not an observed encoder-length failure.

There is no accuracy result and no reliable ETA. The initial 21-hour estimate was a fallback before any completed case supplied timing data. Checkpoints are preserved. The planned run uses GPUs 2 and 3 and the same sparse configuration, with a 32K input cap: longer LongBench contexts are truncated, so this is not the official full-context evaluation protocol.

## Evidence files

Each run directory contains its `plan.json`, `status.json`, `report.json`, and saved worker configurations. The reports below link to the underlying saved results:

- [AIME25 report](../workspace/outputs/aime25-GH/report.json)
- [HMMT25 report](../workspace/outputs/hmmt25-GH/report.json)
- [GPQA report](../workspace/outputs/gpqa-GH/report.json)
- [MMLU partial report](../workspace/outputs/mmlu-GH/report.json) and [worker-0 error log](../workspace/logs/mmlu-GH/ours-worker0.log)
- [SuperGPQA partial report](../workspace/outputs/supergpqa-GH/report.json) and [worker-0 error log](../workspace/logs/supergpqa-GH/ours-worker0.log)
- [LongBench status](../workspace/outputs/longbench-GH/status.json)

This summary does not alter any experiment code, configuration, checkpoint, or saved result.
