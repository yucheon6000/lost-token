# Lost Tokens

Training-free reasoning with memory from short, unchosen continuations.

The main implementation is **ours argmax with vLLM**. Inside reasoning, it briefly
explores two plausible continuations, commits the rank-1 continuation exactly, and
can retain the other as an unverified hint. It produces one final answer, with
additional computation for the short rollouts.

The initial configuration improved accuracy on **five of six full datasets** in
one seed, with an MMLU regression. This is a research candidate, not a demonstrated
multi-seed improvement. [Results, baseline, method and environment](results/argmax-single-seed/README.md)
include the corrected multiple-choice scoring and original execution provenance.
Multi-seed evaluation has not been run for this release.

## Setup and smoke test

Use Linux, an NVIDIA GPU with sufficient memory, and a compatible NVIDIA driver.
The published evaluation used eight RTX PRO 6000 Blackwell GPUs; GPU allocation
is configurable. Memory needs depend on context length and concurrent cases.
The first setup needs internet access and disk space for the local environment,
pinned model weights, datasets and checkpoints. System Python is not modified.

```bash
git clone https://github.com/yucheon6000/lost-token.git
cd lost-token
./scripts/quickstart.sh --gpus 0
```

The bootstrap installs a local `uv` if needed, runs `uv sync --frozen`, downloads
the pinned generator, embedding model and AIME25 data, then runs a short smoke
with interruption, checkpoint replay and audit. The default smoke cap is 256
output tokens: it checks infrastructure and can finish without a final answer.
**Smoke scores are not benchmark results.**

With an existing `uv`:

```bash
uv sync --frozen
uv run --frozen lost-tokens setup --benchmarks aime25
uv run --frozen lost-tokens smoke --benchmarks aime25 --gpus 0
```

If the bootstrap installed `.tools/uv`, substitute it for `uv` in these commands.
Use `--work-dir /path/to/work` for generated data and outputs, and
`--model-cache /path/to/model-cache` to reuse an existing model cache. Pass the
same storage arguments to setup and subsequent runs.

## Evaluate baseline and ours

Packaged defaults exactly match [configs/vllm-argmax.json](configs/vllm-argmax.json).
The default backend is pinned vLLM 0.10.2 V0. Both arms use the same pinned
Qwen3-4B-Thinking-2507 BF16 model, prompts, per-position seeds, repetition guard,
32,768-token input and output caps, temperature 0.6, top-k 20 and top-p 0.95.
Baseline is ordinary AR without branching or memory.

```bash
uv run --frozen lost-tokens setup \
  --benchmarks aime25 hmmt25 gpqa gsm8k math500 mmlu
uv run --frozen lost-tokens run \
  --benchmarks aime25 hmmt25 gpqa gsm8k math500 mmlu \
  --arms baseline ours --gpus 0 --run-name argmax-full
```

Omitting a time budget and `--limit` evaluates every prepared question. Choose
GPU indices allocated to you, for example `--gpus 0,1` for two workers. Each GPU
owns an independent TP=1 model and batches up to eight cases. Run in `tmux` or
your scheduler when disconnecting. Data preparation also supports `--benchmarks
all`, which includes two additional datasets outside the six reported here.

For shared experiments, use the [canonical guide and fixed IDs](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/docs/EXPERIMENT_GUIDE.md).
The `shared-v1` cohort uses subsets for MATH500 and MMLU; the release result table
uses the archived **full-v1** cohort. Do not label a shared subset as a full set
or redraw the canonical IDs. [All experiment results](https://github.com/yucheon6000/lost-token/blob/shared-evaluation/experiment-results/README.md)
remain on `shared-evaluation`.

```bash
uv run --frozen lost-tokens status --run workspace/outputs/argmax-full
uv run --frozen lost-tokens report --run workspace/outputs/argmax-full
uv run --frozen lost-tokens resume --run workspace/outputs/argmax-full
uv run --frozen lost-tokens audit --run workspace/outputs/argmax-full
```

Resume rejects changed code, model, data, config or runtime. It reuses completed
checkpoints and preserves original deadlines for timed runs. Completed arms are
not rerun. Use a new run name to change any condition.

## Method and controls

The released method has rank-1 selection, 64-token rollouts, a raw candidate
probability threshold of 0.2, at least 256 body tokens between branches, an
8,192-token alternative-memory capacity and cosine threshold 0.85. Branching
occurs only inside reasoning. Candidate caches are independent; the selected
rollout is committed exactly. Only unchosen rollout text can enter memory, and
its fixed preamble states that the hint is unverified. Reference answers enter
scoring only.

This is not a completed-answer ensemble. It also is not a one-forward-per-token
method: rollout, memory prefill and embedding costs must be included when
comparing compute. The same output cap does not mean the same FLOPs.

- `baseline`: ordinary AR, no rollout or memory.
- `ours`: rank-1 continuation plus cosine-filtered alternative memory.
- `reference`, `selected`, `all`: existing component ablations.
- [vllm-lookahead.json](configs/vllm-lookahead.json): explicit lookahead control.
- [transformers-argmax.json](configs/transformers-argmax.json): Transformers backend
  with the same argmax method; measure a backend-matched baseline for comparisons.

The controls, independent candidate caches, memory compaction and resume audits
remain available. The promoted default excludes additional verification, answer
ensembles, latent embedding mixing and EM-INF logit optimization.

## Configuration and validation

```bash
uv run --frozen lost-tokens config > my-config.json
# Edit my-config.json, then start a new run:
uv run --frozen lost-tokens run --config my-config.json \
  --benchmarks aime25 --arms baseline ours --gpus 0 --run-name new-config
uv run --frozen python -m unittest discover -s tests -v
uv run --frozen ruff format --check src tests scripts
uv run --frozen ruff check src tests scripts
uv build --wheel
```

Public code is under `src/lost_tokens/`; protocol defaults are in
`default.json`, and dataset URLs, revisions and hashes are in `datasets.json`.
The wheel includes these resources and the `lost-tokens` CLI. Generated data,
weights, environments and inference checkpoints stay under configurable storage
and are excluded from Git. The curated release result snapshot is versioned on
main at the user's request; the full shared experiment archive remains separate.
