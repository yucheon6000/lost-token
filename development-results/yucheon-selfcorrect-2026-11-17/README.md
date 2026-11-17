# Accuracy pilot: allow self-correction language

The candidate improved accuracy on this small development sample without a task-level regression. It is a candidate for full evaluation; this pilot does not establish a universal gain.

**Fresh current Ours: 46/60 (76.67%). Candidate: 49/60 (81.67%). Paired wins/losses: 4/1.**

This is an accuracy experiment on 10 questions from each of six datasets, separate from the preceding inference-consistency diagnostic. The selected IDs are development data. These are not full-cohort benchmark scores and do not enter the canonical comparison index.

| Dataset | Fresh current Ours | Candidate Ours | Difference | Paired wins / losses |
|---|---:|---:|---:|---:|
| aime25 | 7/10 | 8/10 | +10.0 pp | 1 / 0 |
| hmmt25 | 4/10 | 6/10 | +20.0 pp | 2 / 0 |
| gsm8k | 10/10 | 10/10 | +0.0 pp | 0 / 0 |
| gpqa | 7/10 | 7/10 | +0.0 pp | 1 / 1 |
| math500 | 10/10 | 10/10 | +0.0 pp | 0 / 0 |
| mmlu | 8/10 | 8/10 | +0.0 pp | 0 / 0 |

All task sample sizes are equal, so the 60-question aggregate also equals the unweighted mean of the six task accuracies. It is not the weighting of the 2,139-question canonical cohort.

## Change and comparison

Only `experiment.lookahead.contradiction_penalty` changes, from **0.25 to 0.0**. The old rule subtracts 0.25 from a candidate's lookahead score if its text contains `wait,`, `wait.`, `hold on`, `contradiction`, `impossible`, or `mistake`. The hypothesis was that this blanket penalty can punish useful self-correction and valid proof steps.

The two candidates, 64-token lookahead, raw-confidence statistic, selection margin, quality/cosine memory filtering, exact rollout commit, repetition guard, answer reservation, model/tokenizer revisions, random seed, and scorer remain unchanged. The archived-prefix replay changes 186 of 1,989 choices; that replay is a policy-sensitivity result, not an accuracy measurement. See [method.md](method.md).

Both sides were executed fresh with native `--arms ours`: current Ours as the control and the modified Ours as the candidate. Each received two explicitly allocated L40S GPUs on the four-GPU machine, with equal task grouping and maximum batches (8 for GSM8K/GPQA/MATH500/MMLU, 4 for AIME/HMMT). All worker configs are checked to differ only in the declared penalty. This is a paired development allocation, not a new registered hardware profile.

The same 60 label-independent IDs from the consistency diagnostic are reused. The old diagnostic code commit and probe metadata in `sample-manifest.json` describe the sampling provenance, while `pilot-plan.json` pins the execution commit for this accuracy experiment. No dataset labels or reference answers are inserted into prompts.

Dynamic inference paths may still differ between methods. These are measured final-answer outcomes from one paired pilot, not a decomposition of every gain/loss into algorithmic versus numerical effects. A larger evaluation and repeat measurements are needed before a robust improvement claim.

## Completion and cost

| Measurement | Fresh control | Candidate |
|---|---:|---:|
| Missing extracted final answers | 0/60 | 2/60 |
| Forced thinking closures | 6/60 | 2/60 |
| Generated body tokens | 609,314 | 632,402 |
| Elapsed minutes on two allocated GPUs | 78.4 | 84.2 |

Elapsed time includes loading, both task groups, and native audits; the two variants ran concurrently. Per-case elapsed times overlap under batching and must not be added as wall time.

The two candidate extraction failures were inspected. `gpqa-recrTL3i1VEPCfDGy` ended with `**Final answer**: $\boxed{D}$`; its intended letter matches the gold answer, but the fixed scorer rejects this format. It remains incorrect in every published score. `hmmt25-13` reached the output cap after forced thinking closure and had no extracted final answer. The control also answered that HMMT case incorrectly. No scorer or recorded outcome was changed.

The four strict-scoring wins are `aime25-30`, `gpqa-recH879YiAi6dLCSy`, `hmmt25-8`, and `hmmt25-12`. The only loss is the GPQA format failure above. These case-level outcomes are observations; this single pilot does not prove the exact causal contribution of every changed branch.

## Reused references

The earlier quality-memory full run scored **47/60** on these IDs. It used a different task/batch schedule, so the fresh control above is the primary comparison. The frozen AR reference scored **45/60** on the selected IDs and was originally measured on PRO 6000 hardware. It is cross-hardware context, not a matched L40S baseline. No AR inference was rerun. See [baseline.md](baseline.md) for the unchanged reference hash and original provenance.

## Validation and artifacts

- CPU suite: **172 tests passed**. Source CI: [passed](https://github.com/yucheon6000/lost-token/actions/runs/43979534516).
- GPU preflight: four independent GSM8K questions outside the 60-question pilot; all four final answers extracted and scored, **3/4 correct**, all four native audits passed. This checks execution/scoring, not an accuracy gain.
- Main pilot: **120 scored cases**, exactly 60 IDs per variant, all eight worker audits passed. Answer metadata is checked against the audited case files, and source/outcome/case/config hashes are preserved in [completion-proof.json](completion-proof.json).
- [summary.json](summary.json), [paired-outcomes.json](paired-outcomes.json), [environment.json](environment.json), [reports.json](reports.json), [pilot-plan.json](pilot-plan.json), and [sample-manifest.json](sample-manifest.json) preserve the comparison.
- Code branch: [`yucheon-selfcorrect-2026-11-17`](https://github.com/yucheon6000/lost-token/tree/yucheon-selfcorrect-2026-11-17). Execution commit: [`9feae0c947e5c4fa3ea1b0bee2bd675b50019c0d`](https://github.com/yucheon6000/lost-token/tree/9feae0c947e5c4fa3ea1b0bee2bd675b50019c0d).
- Full native checkpoints, generated texts, and model caches remain in the private work directory; large intermediate artifacts are not uploaded. Canonical cohorts, published prior scores, and baseline references are unchanged.

This directory intentionally stays outside `experiment-results/`. Formal evaluation must use the complete registered IDs for its hardware profile; the 60 development IDs must not replace that cohort.

## Reproduction

Use the personal code branch and its prepared pinned datasets/model cache. The [short-task IDs](short-ids.json), [math IDs](math-ids.json), and four [frozen configs](configs/) are published here. The two group commands below reproduce the candidate; run the matching control configs on the other two GPUs for the paired experiment. Use new run names and a private work directory.

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

The control uses `control-short-config.json` / `control-math-config.json`, the same ID files and task orders, `--gpus 0,1`, and distinct control run names. These are development-pilot commands; full evaluation continues to use the complete canonical IDs and hardware-profile guide.
