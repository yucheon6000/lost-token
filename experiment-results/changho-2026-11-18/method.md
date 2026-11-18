# Fixed-roster answer consensus

Objective: exceed the frozen, identically scored AR baseline and previous selected ours on full AIME25 (30), HMMT25 (30), and GPQA Main (448). No guarantees are claimed before fresh validation.

The fixed member order is ordinary AR, memory argmax, memory lookahead, previous answer-reserve policy, previous delayed/long-rollout policy. The last two members use argmax for AIME/HMMT and lookahead for GPQA, exactly as previously configured. Internal reasoning-only branching, independent caches, selected-rollout commits and compaction are unchanged. Each member is a full independent persisted run. There is no sharing of inference checkpoints across members.

The voter sees final prediction strings only. It has no access to gold, reference explanations, member correctness, or the question. Missing finals abstain; all questions stay in the denominator. Math predictions cluster by the locked symbolic equivalence scorer. Most votes wins; ties use the earliest member in the immutable roster. The selected output is an actual member prediction, with the complete source trace preserved. Selecting the known-correct minority is forbidden and tested.

Exploratory cached results were 25/30 AIME, 20/30 HMMT and 289/448 GPQA, above the previous selected ours 24/30, 18/30 and 283/448. This was development on previously inspected data with correlated trajectories. It is not the prospective new-seed validation and is not an unseen-test claim. Full exploratory predictions, ties, member order and paired counts are in exploratory-consensus5.json.

Before new generation, the five-member roster, equal weights, equivalence policy, tie break, base seed, two repeat indices and pooled ten-member secondary report were frozen in pipeline.json and source commit. No roster, seed or decision-rule search is performed after observing the new results. Each member seed is derived_seed(base_seed, protocol, repeat_index, member_name), then the existing deterministic case/position seed logic applies. Both repeats cover all committed shared-v1 IDs for these three complete tasks. Pooled results concatenate repeat 0 then repeat 1 in the same frozen member order; they are not an additional independent validation repeat.

This accuracy-first method costs five complete generations per question per repeat; the pooled result costs ten. It is compared against frozen single-pass controls and must not be presented as equal-compute algorithmic superiority. Plain-AR member runs are components of this new method, not replacement baseline benchmark measurements. The original AR reference and previous runs remain immutable; no baseline score is substituted or refreshed. All comparisons use the same corrected terminal-box extractor. Thus earlier boxed-choice scoring recovery is not counted as a new model gain.

Two allocated fixed-batch single-case-concurrency GPU controls test whether identical seed/config produces identical complete bodies. They are structural/repeatability preflights, not official benchmark scores. Main batched runs retain case concurrency up to eight per GPU. Exact bitwise reproducibility of dynamic batching is not assumed; prospective repeat performance is reported separately.

Every member must complete the exact full ID set with passing ledger audits before its vote is scored. Member outcome hashes, config/source/runtime identities, GPU allocation, seed and times are recorded. Resume uses original runs and deadlines; finished members are revalidated and skipped. Voting happens after selection, and grading is read from the selected member's audited outcome. No ground-truth-dependent oracle is used.

Sources: Wang et al., Self-Consistency Improves Chain of Thought Reasoning in Language Models, https://arxiv.org/abs/2203.11171 . Qwen model sampling guidance: https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507 . Generator weights, sampler temperature 0.6/top-p 0.95/top-k 20, 32K per-path body limit and data adapter remain pinned.

Final code branch follows the actual completion date in Asia/Seoul: changho-YYYY-MM-DD. The internal study/run names retain their initial immutable identities. Raw source/configs used by running jobs are not edited.

## Fixed-batch control result

Both scored GPU controls completed with passing audits. The two canonical GPQA questions produced identical full body-token hashes across GPU 0 and GPU 1 at batch=1. See fixed-batch-control.json. This supports the ability to replay under controlled batching for these two examples; it does not establish the exact cause of dynamic-batch differences or guarantee bitwise equality of the main batch=8 study.

## Recovery after startup failure

The queue stopped on 2026-11-17 during the first GPQA AR ensemble member because vLLM initialization hit EADDRINUSE. It was observed stopped on 2026-11-18 and resumed with identical package source, frozen configurations and runtime. A stale mutable worker heartbeat initially caused the frozen supervisor to report a stall before worker initialization; those previous operational status records were archived and marked resuming. Identity files, inference ledgers, plans, configs and original schedule/deadline were not altered. All 2,839 original checkpoint files were verified byte-identical after resume. See recovery-original.json, recovery-status.json and recovery-checkpoint-verification.json. The external wrapper retries only fresh startup port-collision errors, at most three attempts, and stops for other failures.

The resumed GPQA member phase wall retains its original start and therefore includes overnight downtime. It is not a fresh compute-time measurement; future timing comparisons must separate the interruption from active execution. Completed member outputs and the two completed first-repeat math votes were preserved.

## Completion and primary criterion

Final branch `changho-2026-11-18`, source commit `7ed439b2ba51d588dae364584e3fbebc8bdcdc54`. The user clarified on Nov 18 that exceeding baseline alone is sufficient. Previous ours remains a secondary reference; no generation settings or frozen manifests were changed when the criterion was updated. See evaluation-criterion.json. Both five-path repeats pass this primary criterion across all three full datasets. The pooled ten-path result was predeclared. See summary.md for the completed metrics, costs, limitations and operational recovery.
