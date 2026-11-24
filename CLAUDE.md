# Lost Tokens: main release

Start with `README.md`, `AGENTS.md` and `results/argmax-single-seed/README.md`.
Main promotes the initial **argmax + alternative memory + vLLM** method. Packaged
`default.json` exactly matches `configs/vllm-argmax.json`. Do not silently switch
to lookahead, verification, answer ensembles, SeLaR or EM-INF.

The result snapshot is single-seed, full-v1, and uses corrected multiple-choice
scoring. Historical inference was not regenerated for this publication. Multi-seed
validation is future work and has not been started for this release.

Use `uv sync --frozen` and `uv run --frozen`; keep environments and generated data
local to configurable storage. Preserve reasoning-only branching, independent
candidate caches, exact selected-rollout commit, memory compaction and immutable
checkpoint identities. Do not edit source or configs used by a running job.

Shared experiments use the canonical [guide](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/EXPERIMENT_GUIDE.md)
and fixed IDs on `shared-evaluation`; never redraw them. Read that guide before
shared evaluation. A `shared-v1` subset is not the release's full-v1 cohort.
Personal `{name}-{date}` branches contain code/settings/tests; full reports and
comparison entries go to `shared-evaluation`. The explicitly requested main
release additionally contains a curated result snapshot under `results/`.

Before changes, snapshot originals under ignored `temp/snapshots/`. Run all CPU
unittests after changes, and allocate a free GPU for decoding smoke tests. Verify
README commands, wheel packaging and another working directory when changing the
quickstart or path behavior. Do not start GPU experiments for status or document
requests; a publication validation smoke is distinct from benchmark reruns.
