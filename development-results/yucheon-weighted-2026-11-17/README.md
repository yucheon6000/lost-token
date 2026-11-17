# Accuracy pilot: weight later continuation confidence

Weighted selection decreased total sampled accuracy. The uniform selector remains the preferred method based on this pilot.

**Fresh uniform Ours: 48/60 (80.00%). Weighted Ours: 47/60 (78.33%). Paired wins/losses: 1/2.**

The user requested applying the proposed weights and testing 10 questions from each dataset. This is a paired development accuracy experiment on the same fixed 60 IDs used previously, not a full-cohort benchmark submission. No IDs were redrawn or selected using labels. The sample is development data, not a held-out confirmation set.

| Dataset | Uniform current Ours | Weighted Ours | Difference | Paired wins / losses |
|---|---:|---:|---:|---:|
| aime25 | 7/10 | 7/10 | +0.0 pp | 0 / 0 |
| hmmt25 | 5/10 | 6/10 | +10.0 pp | 1 / 0 |
| gsm8k | 10/10 | 10/10 | +0.0 pp | 0 / 0 |
| gpqa | 8/10 | 6/10 | -20.0 pp | 0 / 2 |
| math500 | 10/10 | 10/10 | +0.0 pp | 0 / 0 |
| mmlu | 8/10 | 8/10 | +0.0 pp | 0 / 0 |

Each task has 10 questions, so total sampled accuracy equals the unweighted mean of the six task accuracies. It is not the weighting of the 2,139-question canonical L40S cohort.

## Applied change

The control is the latest self-correction variant: uniform mean continuation log probability, with the lexical contradiction penalty disabled. The candidate adds only `lookahead.half_weights: [0.25, 0.75]` to branch selection. The forced first candidate token remains excluded. For a full preview:

```text
score = 0.25 * mean(logp of preview tokens 2–32)
      + 0.75 * mean(logp of preview tokens 33–64)
```

That is 31 continuation tokens in the first half and 32 in the second. For shorter previews, split the actual continuation after floor(n/2); original minimum-length and terminal checks remain unchanged. The control uses the original mean over all continuation tokens, not exactly a 50/50 average of the two unequal-length half means.

**Memory filtering remains unchanged.** The quality gate uses the original uniform mean log probability and 0.10 gap. All live event scores are independently checked against the weighted selection formula and uniform memory formula. A changed chosen rank naturally changes which unchosen future can become memory; no new memory-scoring rule is introduced.

Preserved: frozen model, two token candidates, up-to-64-token previews, 0.10 switching margin, disabled word penalty, independent candidate contexts, verbatim selected-rollout commit, cosine filtering, memory capacity/compaction, sampling, prompt/data adapters, scorer, output budget, and answer reservation. No verifier, extra model calls, answer-format normalization, or memory-lifetime change was added. See [method.md](method.md).

The hypothesis is that emphasizing later confidence can reduce branches winning through an easy opening. Confidence remains a proxy for correctness. A policy change or faster run is not sufficient evidence of success; the primary metric is scored final-answer accuracy.

## Experimental comparison

Both sides ran fresh with native `--arms ours`, using two L40S GPUs each concurrently on the four-GPU machine. Both use the same task order and IDs, batch maximum 8 for GSM8K/GPQA/MATH500/MMLU, and 4 for AIME/HMMT. Every pair of worker configs is checked to differ only by the selection half weights. This is a development allocation, not a new registered hardware profile.

The inference source is frozen at the code commit below. Existing configs without half_weights retain their original score calculation and checkpoint fields; CPU golden/replay tests check compatibility. The sampling manifest contains historical diagnostic metadata, while pilot-plan.json pins this experiment's execution and configs.

The preceding self-correction pilot scored **49/60** on these IDs. The fresh concurrent uniform control above is the primary comparator. Dynamic batch/cache paths may differ even under the same nominal settings, so one small pilot does not establish a universal or repeatable gain.

The unchanged frozen AR reference scored **45/60** on these IDs and was originally run on PRO 6000 hardware. It is cross-hardware context, not a matched L40S baseline. No AR inference was rerun. [Reference and provenance](baseline.md).

## Completion and cost

| Measurement | Uniform control | Weighted candidate |
|---|---:|---:|
| Missing extracted answers | 2/60 | 3/60 |
| Forced thinking closures | 4/60 | 5/60 |
| Generated body tokens | 642,270 | 628,218 |
| Elapsed minutes on two allocated GPUs | 83.3 | 85.7 |

Elapsed time includes loading, both task groups, and native audits; the variants ran concurrently. Per-case elapsed times overlap and must not be summed as wall time. Missing or malformed final answers remain incorrect under the unchanged scorer; no after-the-fact rescoring is applied.

## Unextractable-answer observations

The official scores above remain unchanged. Inspection distinguishes budget exhaustion from output formatting; this is not a second scoring scheme.

| Variant | Dataset / ID | Observation |
|---|---|---|
| Weighted | aime25 / `aime25-15` | Body cap exhausted without an extractable final answer |
| Weighted | gpqa / `gpqa-recrTL3i1VEPCfDGy` | A boxed multiple-choice letter is visible, but the unchanged scorer returned null |
| Uniform | gpqa / `gpqa-recoiTJPGUmzAkief` | A boxed multiple-choice letter is visible, but the unchanged scorer returned null |
| Weighted | gpqa / `gpqa-recoiTJPGUmzAkief` | A boxed multiple-choice letter is visible, but the unchanged scorer returned null |
| Uniform | hmmt25 / `hmmt25-13` | Body cap exhausted without an extractable final answer |

A forced thinking closure does not guarantee a final answer: the model can continue reasoning in the reserved answer portion until the body cap. Formatting-related failures also remain incorrect under the frozen scorer. See [failure-analysis.json](failure-analysis.json).

## Paired changes

| Dataset | ID | Control prediction | Candidate prediction | Correctness change |
|---|---|---|---|---:|
| gpqa | `gpqa-recrTL3i1VEPCfDGy` | `D` | `None` | -1 |
| gpqa | `gpqa-reccc0j9BzteLsAB5` | `C` | `D` | -1 |
| hmmt25 | `hmmt25-7` | `\dfrac{15}{8}` | `\dfrac{9\sqrt{23}}{23}` | +1 |

These are measured outcomes, not proof of the causal contribution of any individual branch. All 60 pairs, including unchanged and unextractable answers, are retained in paired-outcomes.json.

## Validation and artifacts

- CPU validation: **181 tests passed**, including weighted arithmetic, forced-first-token exclusion, uniform memory-score isolation, default compatibility, native protocol audit, and resume replay. Source CI: [passed](https://github.com/yucheon6000/lost-token/actions/runs/44003135240).
- GPU preflight: two independent GSM8K questions outside this sample; **2/2 correct**, both native audits passed. All six recorded weighted events also passed an independent uniform-memory-score check.
- Main pilot: **120 scored cases**, exactly 60 per variant, all eight native worker audits passed. Raw outcome fields are checked against audited case files; weighted selection and uniform memory scores are independently recomputed for every recorded event.
- [completion-proof.json](completion-proof.json), [summary.json](summary.json), [paired-outcomes.json](paired-outcomes.json), [reports.json](reports.json), [environment.json](environment.json), [pilot-plan.json](pilot-plan.json), and [sample-manifest.json](sample-manifest.json) retain counts, hashes, settings, and provenance.
- Code branch: [`yucheon-weighted-2026-11-17`](https://github.com/yucheon6000/lost-token/tree/yucheon-weighted-2026-11-17). Frozen execution commit: [`fe06f6db1f0ce3c053c9da24b54e3e6c4080feea`](https://github.com/yucheon6000/lost-token/tree/fe06f6db1f0ce3c053c9da24b54e3e6c4080feea).
- Additional evidence: [preflight.json](preflight.json), [validation.json](validation.json), and [failure-analysis.json](failure-analysis.json). Wheel packaging and all five configs also passed validation from a different working directory.
- Full native checkpoints/generated texts and model caches remain in the private work directory. The canonical cohorts, prior published scores, and frozen baseline reference remain unchanged.

This development report stays outside experiment-results/ and the canonical comparison index. Full evaluation continues to require the complete registered IDs for its hardware profile.

## Reproduction

Use the personal code checkout with the pinned prepared datasets and model cache. Published [configs](configs/), [short-task IDs](short-ids.json), and [math IDs](math-ids.json) reproduce the candidate as follows. Use private work storage and new run names:

```bash
uv run --frozen lost-tokens run --config /path/to/report/configs/candidate-short-config.json \
  --work-dir workspace --model-cache /path/to/model-cache \
  --benchmarks gsm8k gpqa math500 mmlu --gpus 2,3 --arms ours \
  --ids-file /path/to/report/short-ids.json --run-name YOUR-candidate-short
uv run --frozen lost-tokens run --config /path/to/report/configs/candidate-math-config.json \
  --work-dir workspace --model-cache /path/to/model-cache \
  --benchmarks aime25 hmmt25 --gpus 2,3 --arms ours \
  --ids-file /path/to/report/math-ids.json --run-name YOUR-candidate-math
```

For the paired control, use control-short-config.json / control-math-config.json, identical ID files and task orders, --gpus 0,1, and distinct run names. These sampled commands are for development, not replacements for the full canonical evaluation.
