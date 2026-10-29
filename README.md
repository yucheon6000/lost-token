# Lost Tokens

**Reusing Unchosen Reasoning Branches as In-Context Memory**

Lost Tokens is a training-free decoding method. While a model is inside `<think>`,
at positions where two next tokens are both plausible it rolls both out for a few
dozen tokens, commits the rollout whose continuation is more confident, and keeps
the other one in its context as an unchosen possibility. This repository compares
ordinary autoregressive decoding (`baseline`) with that method (`ours`).

## One-command setup and smoke test

Linux, an NVIDIA GPU, and a compatible NVIDIA driver are required for the GPU
quickstart. A 24 GB GPU was used for the default 4B model; peak usage depends on
context length. Allow roughly 20 GB for the environment and model downloads, plus
space for datasets and experiment checkpoints. `curl` and `git` are needed for
bootstrapping. No system Python packages or CUDA toolkit installation are needed.

```bash
git clone https://github.com/ccho4702/lost-tokens.git
cd lost-tokens
./scripts/quickstart.sh
```

This installs `uv` into `.tools/` if it is unavailable, creates a project-local
Python 3.12 `.venv` from `uv.lock`, downloads the pinned generator, embedding model
and AIME25 dataset, prepares the data, and runs a short baseline/ours smoke test on
GPU 0. The smoke test deliberately interrupts and resumes workers, verifies saved
checkpoints, and audits the completed reasoning traces. **Smoke scores are not
benchmark scores.** Model downloads require internet access the first time.

Arguments are forwarded to the quickstart CLI:

```bash
./scripts/quickstart.sh --gpus 0,1 --benchmarks aime25 gpqa --work-dir ./workspace
```

Already have `uv`? The equivalent explicit commands are:

```bash
uv sync --frozen
uv run --frozen lost-tokens setup --benchmarks aime25
uv run --frozen lost-tokens smoke --benchmarks aime25 --gpus 0
```

If the bootstrap installed a local `uv`, use `.tools/uv` in place of `uv`.

## Run an evaluation

```bash
# Download and prepare any subset, or use --benchmarks all.
uv run --frozen lost-tokens setup --benchmarks aime25 supergpqa

# All selected GPUs run baseline for 3 hours, then ours for 3 hours.
uv run --frozen lost-tokens run \
  --benchmarks aime25 supergpqa --gpus 0,1,2,3 \
  --hours-per-arm 3 --run-name aime-super-6h

# Omit --hours-per-arm to finish the full selected dataset(s).
# --limit is a deterministic per-benchmark subset, applied identically to both arms.
uv run --frozen lost-tokens run \
  --benchmarks aime25 --gpus 0 --limit 2 --run-name two-case-check
```

GPU count is configurable; one GPU is fully supported. GPU numbers are indices
within `CUDA_VISIBLE_DEVICES` when that variable is set. Each GPU runs one
independent worker. Both arms use identical shuffled questions, disjoint shards,
per-case seeds, and output limits. The arms run sequentially, using the same GPUs.
The time budget includes model loading; final CPU audits may finish later.
Launch in `tmux` or your job scheduler when disconnecting from a server.

```bash
uv run --frozen lost-tokens status --run ./workspace/outputs/aime-super-6h
uv run --frozen lost-tokens report --run ./workspace/outputs/aime-super-6h
uv run --frozen lost-tokens resume --run ./workspace/outputs/aime-super-6h
uv run --frozen lost-tokens audit --run ./workspace/outputs/aime-super-6h
```

Resume reuses atomic inference checkpoints and rejects changed model, data,
configuration, code, or runtime identities. Resuming a timed run preserves its
original deadlines; it does not grant a fresh budget. Completed earlier arms are
not rerun. Start a new run name to change the experiment.

## Ablation arms and seeds

`run --arms` selects which arms to run, sequentially in the given order. The
default is `baseline ours`. The other arms are `ours` with one component removed:

| Arm | Rolled out | Committed | Inserted into context |
|---|---|---|---|
| `baseline` (plain_ar) | nothing | sampled tokens | nothing |
| `reference` (reference_only) | rank 1 only | rank 1 | nothing |
| `selected` (selected_only) | both | selected rollout | nothing |
| `all` (all_futures) | both | selected rollout | the other rollout, unfiltered |
| `ours` (filtered_futures) | both | selected rollout | the other rollout if not near-duplicate |

When `baseline` is in the run, the report adds a paired table (common n, wins,
losses, difference pp) for every other arm; without `baseline` it reports
per-arm accuracy only.

```bash
uv run --frozen lost-tokens run --benchmarks aime25 --gpus 0,1 \
  --arms reference --run-name aime25-reference
```

Per-case seeds derive from `experiment.seed`, the dataset namespace and the row
id, so they are identical across arms and across runs with the same seed. To
change the seed, export the config, edit `experiment.seed`, and pass it with a
new run name:

```bash
uv run --frozen lost-tokens config > seed2.json   # edit "experiment": {"seed": ...}
uv run --frozen lost-tokens run --config seed2.json --benchmarks aime25 \
  --arms baseline reference ours --run-name aime25-seed2
```

Compare runs offline (stdlib only), pairing each arm with a baseline run/arm:

```bash
python scripts/compare_runs.py RUN_A RUN_B --baseline RUN_A:baseline
```

### Experiment knobs

Method keys in `experiment` (defaults in [`default.json`](src/lost_tokens/default.json)):

- `branch_tokens` (64): rollout length including the forced first token.
- `selection`: `"lookahead"` (default) or `"argmax"`. Lookahead scores each rollout
  by its continuation after the forced first token, with `lookahead.statistic`
  either `mean_logprob` (mean raw log-probability of the sampled tokens) or
  `neg_mean_entropy` (negative mean next-token entropy). The alternative is
  committed instead of rank 1 when its score is better by at least
  `lookahead.margin` nats per token (0.1) and it has at least
  `lookahead.min_tokens` continuation tokens (16), non-blank text and did not end
  thinking or the response. Otherwise rank 1 is committed. `"argmax"` always
  commits rank 1 and requires `lookahead: null`.
- `memory_preamble`: one fixed line written at the top of every `<possibilities>`
  block, or `null` for none. It is escaped like rollout text and audited with it.
- `min_candidate_probability` (0.20), `min_branch_interval_tokens` (256) and the
  `similarity.threshold` (0.85) control when a fork happens and when the
  alternative is inserted.

Optional keys that are off when absent or `null`: `max_memory_events`,
`min_branch_body_tokens`, `memory_ttl_tokens` and `budget_forcing`
(`{"force_at_body_tokens", "answer_tokens"}`, `plain_ar` only).

## Data and configuration

| CLI name | Dataset | Questions |
|---|---|---:|
| `aime25` | [MathArena AIME 2025](https://huggingface.co/datasets/MathArena/aime_2025) | 30 |
| `hmmt25` | [MathArena HMMT February 2025](https://huggingface.co/datasets/MathArena/hmmt_feb_2025) | 30 |
| `gpqa` | [GPQA Main, original public archive](https://github.com/idavidrein/gpqa) | 448 |
| `supergpqa` | [SuperGPQA](https://huggingface.co/datasets/m-a-p/SuperGPQA) | 26,529 |
| `longbench_v2` | [LongBench v2](https://huggingface.co/datasets/zai-org/LongBench-v2) | 503 |

Dataset revisions, download URLs, and SHA256 hashes are pinned in
[`datasets.json`](src/lost_tokens/datasets.json). GPQA uses the original authors'
public ZIP and documented password. Downloads are verified before use; datasets
and model weights are not redistributed in this repository. Their original
licenses and access terms apply. `download` and `prepare` are also available as
separate commands; `setup` runs both, including model downloads.

Defaults live in [`default.json`](src/lost_tokens/default.json). Export and edit a
configuration to change models or method parameters:

```bash
uv run --frozen lost-tokens config > my-config.json
uv run --frozen lost-tokens setup --config my-config.json --benchmarks aime25
uv run --frozen lost-tokens run --config my-config.json --benchmarks aime25 --gpus 0
```

Default generator: **Qwen/Qwen3-4B-Thinking-2507**, BF16. Embeddings:
**Qwen/Qwen3-Embedding-0.6B**, CPU float32. Both revisions are pinned. Input cap:
**32,768 tokens**; generated body cap: **32,768 tokens**. LongBench retains the
context head and tail while preserving the full question and options; this is a
32K-input evaluation, not the full-context official benchmark. Other datasets
must fit the input cap or preparation fails rather than silently truncating them.

The method forks where the two most probable next tokens both have raw
probability **≥0.20**, at most once per **256 generated tokens**. Both candidates
get an independent KV cache and a **64-token rollout**. The rollout with the more
confident continuation is committed (lookahead, margin 0.1 nats per token); the
other is inserted into the context just before the commit unless its cosine
similarity to the committed rollout is **≥0.85**. Inserted blocks are compacted
away when they exceed 8,192 tokens; generated tokens are never removed. Branching
stops once reasoning ends. See [the protocol](docs/method.md).

All generated files are relative to `--work-dir` (default `./workspace`). Use
`--model-cache` to share an existing Hugging Face cache; no source edits are needed
when moving to another machine. Custom paths are command-line inputs, not
machine-specific constants in the code.

```text
workspace/
  models/          # Hugging Face model cache
  inputs/          # pinned raw data
  intermediates/   # resumable normalized rows and validation hashes
  outputs/        # plans, checkpoints, predictions, audits, report.json/report.md
  logs/           # controller/worker logs and health snapshots
```

## Results

Exploratory results through September 22, 2026, using
**Qwen3-4B-Thinking-2507** and the **previous protocol**: 32-token rollouts, every
candidate with probability ≥0.20 rolled out, rank 1 always committed, no preamble.
To reproduce that protocol with the current code, set `branch_tokens: 32`,
`selection: "argmax"`, `lookahead: null` and `memory_preamble: null`; the current
code still rolls out only one alternative, so results will not be identical. No
results with the current defaults have been recorded yet. Each row compares the
same questions completed by both arms; accuracy includes correct/total counts.
Differences are percentage points.

| Benchmark | Baseline | Ours | Difference |
|---|---:|---:|---:|
| LongBench v2 | **44.86% (48/107)** | 42.06% (45/107) | -2.80 |
| HMMT25 | 43.33% (13/30) | **56.67% (17/30)** | +13.33 |
| GPQA Main | 50.00% (53/106) | **51.89% (55/106)** | +1.89 |
| AIME25 | 70.00% (21/30) | **76.67% (23/30)** | +6.67 |
| SuperGPQA | 41.67% (45/108) | **42.59% (46/108)** | +0.93 |
| **Pooled questions** | **47.24% (180/381)** | **48.82% (186/381)** | **+1.57** |

These runs used 32K input/output caps. HMMT25 and AIME25 cover all 30 questions
each; the other rows are partial evaluations. LongBench v2 uses truncated context.
LongBench v2/HMMT25/GPQA include an additional ours run to complete the shared
cohort, so their compute budgets are unequal. AIME25/SuperGPQA shared a three-hour,
four-GPU budget per arm: baseline completed 183 SuperGPQA questions and ours 108;
the table uses their 108 common questions. The pooled row is question-weighted,
not a benchmark-average score or an equal-compute comparison.

Reports compare **common completed questions**, with per-task accuracy, wins/losses,
completion counts, and runtime. Time-censored subsets can favor quickly completed
questions; they are not full-dataset scores. Selected-rollout commit changes the
main continuation too, so baseline vs ours is not a memory-only ablation.

```bash
uv run --frozen python -m unittest discover -s tests -v
uv build
```

CPU tests cover reasoning-only intervention, independent caches, deterministic
replay, memory compaction, numeric/choice scoring, dataset adapters, paired
reporting and deadlines. The `smoke` command adds real-model GPU and resume tests.
Run it on each new machine before a long evaluation. Python dependencies are
locked; GPU kernels and hardware can still introduce nondeterminism.
