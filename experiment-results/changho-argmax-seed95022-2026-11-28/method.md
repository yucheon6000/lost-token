# Native argmax, seed 95022

[Final Best 3 / full-five report](../changho-argmax-multiseed-2026-11-28/README.md).
Index metadata seed=95022; counts in submission.json and the shared single-seed comparison index are unique full-cohort counts for this seed only. Aggregate repeated-seed counts are in the linked report.

Code/reproduction branch: `changho-argmax-selected-mmlu-2026-11-28`, commit `6d83f6789d471fc3960492c7b17d5bbab03a54af`. Original controller identities and source hashes are in provenance.json; no benchmark inference was repeated to publish these results.
Method: reasoning-only branching when two ordinary next tokens each have raw probability >=0.2, independent 64-token rollouts, exact rank-1 rollout commit, unchanged cosine alternative-memory filtering (0.85), branch spacing256, memory8192 compacted to4096. One final answer, no completed-answer ensemble or seed voting. Output cap32768; additional speculative rollouts and memory prefill mean equal output caps are not equal FLOPs.
Baseline: plain AR with the common repetition guard. Each same-seed/task baseline was audited and sealed before ours. Publication only repackages the frozen results into the common reference schema; original seals, source identities and outcomes are not modified.
Hardware: 8 × NVIDIA RTX PRO 6000 Blackwell Server Edition, BF16, TP1, max8 cases/GPU. Environment and each worker identity record exact runtime/model/GPU metadata.
All listed rows cover the complete fixed full-v1 IDs and pass worker audits. Missing MMLU for seed95024 is explicitly unmeasured. Source seed95022 baseline wall time includes a recorded priority pause; pause-ledger.json preserves the interval and it must not be interpreted as uninterrupted throughput.
Best3 selection was post-hoc on the five non-MMLU benchmarks; all ten choices and the unselected full-five reference remain visible. The selected set was fixed before generating the missing MMLU seed95023. No MMLU-based reselection.
Unmeasured benchmarks: none.
