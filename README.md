# Lost Tokens

**Reusing Unchosen Reasoning Branches as In-Context Memory**

Lost Tokens is a training-free decoding method. While a model is inside `<think>`,
it briefly explores plausible continuations, keeps distinct unchosen branches as
in-context memory, and continues reasoning. This repository compares ordinary
autoregressive decoding (`baseline`) with recurrent branch memory (`ours`).

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

The original method uses **32-token candidate rollouts**, **256 generated tokens
between branch points**, candidate probability **≥0.20**, and cosine threshold
**0.85**. Each candidate has an independent KV cache. Only distinct unchosen
branches enter memory; the highest-probability candidate is committed verbatim
after that memory. Memory compaction removes old memory blocks, preserving the
generated body. Branching stops once reasoning ends. See [the protocol](docs/method.md).

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

## Results and verification

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

See [release verification](docs/verification.md) for the installation, portability,
GPU recovery, and audit checks performed on this implementation.
