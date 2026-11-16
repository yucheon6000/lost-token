# Inference consistency: 10 questions from each of six datasets

**The current runtime is repeatable under identical execution conditions, but changing cache/prefill/batch paths can change Ours decisions. No candidate-induced parent-cache corruption was observed in this sample.**

This is the user-requested diagnostic of 60 questions, not a new accuracy evaluation or replacement cohort. Existing benchmark submissions, canonical IDs, scores, and baseline references are unchanged. No AR benchmark arm was run.

## Sample and environment

- Source: `yucheon-memory-2026-11-16`, method commit `2c8b4870afab764f51cf5092467add4a3832f801`.
- Sample: 10 IDs per task from the registered `l40s-2h-v1` IDs, selected by the lowest SHA256 of `lost-tokens/consistency-v1/{task}/{id}`. Labels, predictions, correctness, and error categories were not used for selection. Exact IDs and source-case hashes: [manifest.json](manifest.json).
- Two prefixes per question: first fork and middle fork (`event_count // 2`). One sampled AIME case also supplied its first compaction prefix: **121 prefixes across 60 questions**. Every reconstructed event and final-context digest matched the original saved ledger.
- Four explicitly allocated, initially idle NVIDIA L40S GPUs. Pinned Qwen3-4B-Thinking-2507 revision, BF16, vLLM 0.10.2 V0; production prefix caching, chunked prefill, and CUDA-graph settings retained. AIME/HMMT maximum batch 4, other tasks 8. Distinct questions fill each diagnostic batch.
- Each GPU worker took 256.6–305.5 seconds after initialization; workers ran concurrently with staggered starts. Main GPU stage was roughly six minutes including loading, excluding harness preparation and the initial failed smoke. All four workers exited successfully and GPUs were released.
- The initial smoke found two diagnostic-harness issues (chat-boundary EOS replay and the engine stop-token suffix). Both were fixed before the reported run; no partial failed-smoke results enter these counts.

## Comparisons

Every comparison fixes the complete token-ID prefix, including memory, and verifies its SHA256. Fresh and batched requests reset prefix caching and recorded zero cached tokens for the target. Warm requests recorded positive cache hits. We captured raw logits before sampling, temperature, repetition guards, or forced diagnostic EOS.

“Incremental” means freshly prefilling the earlier prefix, then replaying **up to the last 64 generated context tokens** one at a time. This tests prefill versus decode behavior without regenerating long answers. It does not replay the entire context token by token.

For parent isolation, the same warm parent is queried before and after independently seeded real candidate rollouts (up to 64 tokens each). Parent context IDs and generated-body IDs are also asserted unchanged. The compaction-only prefix is excluded from the parent-isolation denominator because it has no candidate event.

| Comparison | Prefixes | Identical complete logits | Top-token changes | Fork-gate changes | Largest probability difference |
|---|---:|---:|---:|---:|---:|
| Fresh repeat | 121 | 121/121 | 0 | 0 | 0.0000 pp |
| Same-batch repeat | 121 | 121/121 | 0 | 0 | 0.0000 pp |
| Parent before/after candidate rollouts | 120 | 120/120 | 0 | 0 | 0.0000 pp |
| Batch vs fresh singleton | 121 | 12/121 | 5 | 4 | 7.5453 pp |
| Warm cache vs fresh | 121 | 2/121 | 4 | 3 | 6.2387 pp |
| Incremental suffix vs fresh | 121 | 0/121 | 5 | 1 | 6.9865 pp |

A fork-gate change means the actual production eligibility decision changed: top token non-special, with both non-special candidates at probability ≥0.20. Top-token statistics use the production CUDA `topk(6)` path. Tied ranks count as changes when the actual production rank changes: four of the five batch top-token changes involve a tie in at least one condition, while one is a strict rank reversal. Auxiliary saved `top20` orders can break ties differently and are not used for the reported top-token counts.

| Dataset | Questions | Prefixes | Batch top-token changes | Batch fork-gate changes | Fixed-text branch-selection changes | Fixed-text memory-gate changes |
|---|---:|---:|---:|---:|---:|---:|
| aime25 | 10 | 21 | 1 | 2 | 0/10 | 0/10 |
| hmmt25 | 10 | 20 | 0 | 0 | 0/10 | 0/10 |
| gsm8k | 10 | 20 | 1 | 0 | 0/10 | 0/10 |
| gpqa | 10 | 20 | 1 | 2 | 0/10 | 2/10 |
| math500 | 10 | 20 | 2 | 0 | 0/10 | 0/10 |
| mmlu | 10 | 20 | 0 | 0 | 0/10 | 0/10 |

Dataset-specific warm-cache and incremental counts, full-vocabulary difference summaries, and concrete changed-prefix examples are in [summary.json](summary.json). Batch execution changed the top token or fork eligibility on at least one checked prefix in **8 of 60 questions**.

## What changed and what remained stable

At the first recorded fork of `gpqa-recxWirvTOyWz2zja`, with the exact same 154-token prefix, the second candidate’s probability was **0.2175496** in fresh singleton prefill and **0.1994956** in a batch of eight. The 0.20 gate changes from fork to no fork. This is a decision change before any new memory is inserted.

For the 60 middle-fork pairs we separately teacher-forced the **same two saved candidate continuations** under singleton and batch execution. Recomputed 64-token lookahead selection changed **0/60**, while the pre-cosine memory-quality gate changed **2/60**, both in GPQA. These are conditional fixed-text comparisons; they do not generate different answers or measure counterfactual accuracy.

For `gpqa-recxWirvTOyWz2zja`, the unchosen candidate’s mean continuation-score deficit was **0.0976178** in singleton execution and **0.1018308** in batch execution, crossing the 0.10 memory-quality cutoff. For `gpqa-recrTL3i1VEPCfDGy`, the corresponding deficits were **0.0990944 → 0.1024017**. Both alternatives were kept by the singleton quality gate and rejected by the batched quality gate. Cosine retention was not re-evaluated as part of this diagnostic.

One sampled case (`aime25-30`) contained compaction. Its 25,451-token rebuilt context matched the recorded ledger, preserved generated body tokens, and produced the same top token and fork decision when the obsolete pre-compaction context had been cached. Complete logits differed from a cold rebuild; the maximum normalized-probability difference was **1.07e-6**. This is one observed compaction, not broad compaction coverage.

## Interpretation and next experiment

Identical execution paths were bitwise stable across all repeated fresh and batched comparisons. All 120 candidate-isolation checks were bitwise stable. This provides no evidence of parent-cache contamination from sibling rollouts in the tested conditions.

Execution-path sensitivity is reproduced: identical prefixes can receive different distributions, rankings, or threshold decisions when prefill, incremental decode, cache reuse, or batch composition changes. BF16 and shape-dependent kernels are plausible contributors, but this diagnostic does not isolate a particular kernel, precision operation, or cache implementation as the cause. It does not rule out every possible cache bug.

Before attributing further accuracy gains to a method change, test a controlled inference configuration on these same probes and measure repeated-run answer variance on fixed IDs. Reduced batching, different numerical precision, eager execution, or another backend should be treated as candidate controls and measured; none is established here as a fix. Existing reported accuracies remain measurements of their original runs; these checks do not quantify how much of any score difference arose from runtime sensitivity.

## Artifacts and reproduction

- [Diagnostic audit](diagnostic-audit.json): **passed**. Checks exact coverage, source/case/config/prefix hashes, fresh cache misses and warm hits, finite logits, independently recomputed full-vocabulary differences, recomputed fixed-text selection/quality gates, and all worker completions. This is an artifact-consistency audit, not proof of answer correctness or inference equivalence.
- [Summary](summary.json), [frozen sample](manifest.json), per-prefix observations/comparisons under `workers/`, and engine logs under `logs/` are preserved here. Full-vocabulary `.npz` vectors and reconstructed token-prefix inputs remain in the local diagnostic work directory; their hashes are in the audit. Large vectors and model caches are not uploaded.
- Diagnostic source branch: [`yucheon-consistency-2026-11-17`](https://github.com/yucheon6000/lost-token/tree/yucheon-consistency-2026-11-17).
- Frozen GPU-execution code: [`cc04a32e1cf93ad1bd28d283e2df48f384bc10fb`](https://github.com/yucheon6000/lost-token/tree/cc04a32e1cf93ad1bd28d283e2df48f384bc10fb).
- Audit/export code: [`aa558bbbc6c0a27acffa5e9e9ae6e67e0c4384c7`](https://github.com/yucheon6000/lost-token/tree/aa558bbbc6c0a27acffa5e9e9ae6e67e0c4384c7).
- CPU validation: **177 tests passed**; Ruff format/lint passed. No Ours inference implementation or benchmark scorer was changed.

**CI limitation:** the [source-branch CI](https://github.com/yucheon6000/lost-token/actions/runs/43971397698) passes 176/177 tests; the existing `test_defaults_match_pre_change_golden` exact fingerprint fails on its CPU runner. All five new diagnostic tests pass. The full local suite passes 177/177. A separate local CPU-feature control passes all 29 knob tests with `ATEN_CPU_CAPABILITY=avx2`, while `ATEN_CPU_CAPABILITY=default` fails only that same strict fingerprint test. The inference source, configs, tiny-model fixture, and golden fixture are unchanged from the evaluated method. This demonstrates CPU sensitivity of that fixture; the precise GitHub-runner arithmetic difference remains unisolated. No golden was regenerated or assertion weakened. The diagnostic audit and [shared-report CI](https://github.com/yucheon6000/lost-token/actions/runs/43971502641) pass. Logs and statuses: [validation.json](validation.json), `validation/`.

Run from the personal code checkout, with original saved source runs available. CLI paths below are placeholders:

```bash
uv sync --frozen
uv run --frozen python scripts/check_inference_consistency.py prepare \
  --work-dir workspace/consistency-v1 --shared-root /path/to/shared-evaluation \
  --source-root /path/to/saved/outputs --run-prefix ORIGINAL_RUN_PREFIX \
  --config /path/to/original/task-configs/aime25.json --count 10

# Run these four commands concurrently after checking/allocating free GPUs.
CUDA_VISIBLE_DEVICES=0 uv run --frozen python scripts/check_inference_consistency.py worker --work-dir workspace/consistency-v1 --tasks aime25 --worker-name gpu0
CUDA_VISIBLE_DEVICES=1 uv run --frozen python scripts/check_inference_consistency.py worker --work-dir workspace/consistency-v1 --tasks hmmt25 --worker-name gpu1
CUDA_VISIBLE_DEVICES=2 uv run --frozen python scripts/check_inference_consistency.py worker --work-dir workspace/consistency-v1 --tasks gsm8k math500 --worker-name gpu2
CUDA_VISIBLE_DEVICES=3 uv run --frozen python scripts/check_inference_consistency.py worker --work-dir workspace/consistency-v1 --tasks gpqa mmlu --worker-name gpu3

uv run --frozen python scripts/summarize_inference_consistency.py \
  workspace/consistency-v1 --source-method-commit 2c8b4870afab764f51cf5092467add4a3832f801
```

This directory intentionally stays outside `experiment-results/`: a 10-question forward diagnostic must not enter the canonical accuracy comparison index as a benchmark submission.
