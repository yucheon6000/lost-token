# Expanded weighted Ours evaluation

**Weighted Ours scored 143/180 (79.44%)** on all 30 AIME25, all 30 HMMT25, and 30 selected questions each from GSM8K, GPQA Main, MATH500 and MMLU.

| Dataset | Scope | Weighted Ours | Accuracy | Unextractable |
|---|---|---:|---:|---:|
| aime25 | full dataset | 24/30 | 80.00% | 1 |
| hmmt25 | full dataset | 18/30 | 60.00% | 2 |
| gsm8k | sample of registered L40S IDs | 29/30 | 96.67% | 0 |
| gpqa | sample of registered L40S IDs | 19/30 | 63.33% | 2 |
| math500 | sample of registered L40S IDs | 30/30 | 100.00% | 0 |
| mmlu | sample of registered L40S IDs | 23/30 | 76.67% | 0 |
| **Total** | **Expanded development evaluation** | **143/180** | **79.44%** | **5** |

## What was run

The user requested a larger rerun after the 10-question-per-dataset pilot. Only weighted Ours ran, using native `--arms ours` on four L40S GPUs. Every one of the 180 questions was generated afresh; previous inference outcomes or checkpoints were not imported. No AR baseline or fresh uniform-selector control ran. The existing AR reference remains unchanged.

The method remains exactly `lookahead.half_weights: [0.25, 0.75]`. Selection excludes the forced first token. For a full 64-token preview:

```text
score = 0.25 * mean(logp of preview tokens 2–32)
      + 0.75 * mean(logp of preview tokens 33–64)
```

For shorter previews, split the actual continuation after floor(n/2). The minimum continuation length and terminal checks are unchanged. Memory filtering retains the original uniform mean and 0.10 gap. The model, two token candidates, exact selected-rollout commit, cosine gate, sampling, 32K body cap, answer reservation, prompts, and scorer are unchanged. No verifier or answer normalization was added.

## IDs and scope

AIME25 and HMMT25 each use all 30 pinned prepared evaluation questions. For the other four tasks, the first 30 IDs by `SHA256("lost-tokens/consistency-v1/{task}/{id}")` are taken from their registered L40S ID pools. This is the same ordering used in the previous 10-question sample, so its 10 questions are retained and 20 are added. Labels and model predictions are not inputs to ID selection. [Frozen IDs and selection manifest](sample-manifest.json).

This is a user-requested expanded development evaluation, not the full registered L40S cohort. In particular HMMT uses 30 questions rather than the registered L40S 25. All previous 60 development questions are included, so it is not a held-out confirmation set. Canonical subsets and published full-cohort results were not changed. The equal task sizes give a six-task macro average, not the 2,139-question cohort distribution.

## Comparison limits

The reused frozen AR reference scored 137/180 on exactly these IDs, but it was measured on PRO 6000 hardware. It is context rather than a matched L40S measurement. Original identity, selected-ID counts and paired outcomes are retained in [baseline.md](baseline.md) and [paired-outcomes.json](paired-outcomes.json). No AR inference was rerun.

This larger weighted-only run measures its accuracy; it does not by itself isolate the effect of weighting. The preceding pilot had a fresh uniform control of 48/60 and weighted Ours of 47/60. Historical overlap with the new run is recorded below, with a different four-GPU allocation and batch composition. It is not a new matched selector comparison.

| Dataset (same previous 10 IDs) | Previous uniform | Previous weighted | New weighted rerun |
|---|---:|---:|---:|
| aime25 | 7/10 | 7/10 | 8/10 |
| hmmt25 | 5/10 | 6/10 | 5/10 |
| gsm8k | 10/10 | 10/10 | 10/10 |
| gpqa | 8/10 | 6/10 | 6/10 |
| math500 | 10/10 | 10/10 | 10/10 |
| mmlu | 8/10 | 8/10 | 8/10 |

Same nominal seeds do not guarantee identical outputs under changed dynamic batching and numerical execution paths. [All 60 overlap pairs and original hashes](previous-60-overlap.json).

## Completion, duration and audits

- All **180/180** requested cases are scored; **all eight native worker audits passed**. Every outcome is checked against its hash-audited case, pinned gold answer and frozen source fingerprint. All 5,886 recorded events independently pass the weighted selection formula and unchanged uniform memory-score checks.
- Unextractable answers: **5/180**; forced thinking closures: **11/180**; natural/forced thinking tag incomplete: **0/180**. A forced thinking closure can still be followed by further reasoning until the body cap; it does not guarantee an extractable final answer.
- Elapsed wall time: **133.3 minutes** on four L40S GPUs, including model loading, both groups and native audits. Math tasks use max batch 4/GPU; the other tasks use 8/GPU. TP=1, one model per GPU. Generated body tokens: **1,801,567**. These are execution costs, not evidence of accuracy improvement.
- Malformed or missing final answers remain incorrect under the unchanged scorer. [Failure annotations](failure-analysis.json) do not award extra credit or rescore outputs.
- No code/config/runtime changes were made during the run. The identical source had already passed 181 CPU tests, source CI, wheel/different-CWD validation, and a two-question scored GPU preflight (2/2 correct, both audits passed). These earlier checks are identified as reused validation rather than new runs: [source-validation.json](source-validation.json), [preflight.json](preflight.json).

Code: [`yucheon-weighted-2026-11-17`](https://github.com/yucheon6000/lost-token/tree/yucheon-weighted-2026-11-17); frozen execution commit [`fe06f6db1f0ce3c053c9da24b54e3e6c4080feea`](https://github.com/yucheon6000/lost-token/tree/fe06f6db1f0ce3c053c9da24b54e3e6c4080feea). Source CI: [passed](https://github.com/yucheon6000/lost-token/actions/runs/44003135240).

[Completion proof](completion-proof.json), [study plan](study-plan.json), [summary](summary.json), [native reports](reports.json), [environment](environment.json), [method](method.md), and [configs](configs/) preserve provenance. Full native generated texts and checkpoints remain in the private work directory. This report stays outside the canonical experiment-results index.

## Reproduce the weighted-only expanded run

Use the frozen personal source checkout, its pinned prepared datasets, and the published configs/IDs. Use new private output run names:

```bash
uv run --frozen lost-tokens run --config /path/to/report/configs/math-config.json \
  --work-dir workspace --model-cache /path/to/model-cache \
  --benchmarks aime25 hmmt25 --gpus 0,1,2,3 --arms ours \
  --ids-file /path/to/report/math-ids.json --run-name YOUR-expanded-math
uv run --frozen lost-tokens run --config /path/to/report/configs/short-config.json \
  --work-dir workspace --model-cache /path/to/model-cache \
  --benchmarks gsm8k gpqa math500 mmlu --gpus 0,1,2,3 --arms ours \
  --ids-file /path/to/report/short-ids.json --run-name YOUR-expanded-short
```
