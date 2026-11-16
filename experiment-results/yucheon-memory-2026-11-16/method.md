# Method: yucheon-memory-2026-11-16

## Hypothesis

Reducing lower-confidence alternative memory may improve consistency across six benchmarks. Precommit one 0.1 threshold without official-set hyperparameter search; report every gain, tie and loss versus latest Ours, plus exact-ID cross-hardware reference AR. Do not claim universal improvement unless all six actually improve.

## Implementation

Quality-filtered memory: before unchanged cosine deduplication, retain only eligible unchosen rollouts with unpenalized continuation mean logprob at least selected minus 0.1 nats/token. Forced first token excluded. Selection and doubt penalty unchanged; chosen rollout committed verbatim. Existing 30720/2047 answer reserve, 24576 branch cap, cosine band, model, prompts, sampling, seeds and 32768 total body budget unchanged. Ours only; matched L40S AR unmeasured, existing PRO 6000 AR shown separately as reference.

Code branch: `yucheon-memory-2026-11-16`; commit: `2c8b4870afab764f51cf5092467add4a3832f801`.
Canonical shared checkout commit: `ce9f8a0d748491967db054698be74d57f88e0a1b`.

Only filtered_futures (Ours) was executed. The frozen base config lists available methods; the study and all run plans select only ours. The paired comparison uses latest Ours on L40S with identical protected conditions. A separate existing PRO 6000 AR reference is aligned by exact IDs; it is not a matched L40S baseline.

Cohort manifest SHA256: `6fdcd29e0148339bb2e7541099ad69b93f5bb8e79f3e8ce5885bd222a88ed0ba`
Hardware profile: `l40s-4gpu`.
Task-specific resolved configs (including batch size) are in study-plan.json/task_specs.

## Frozen configuration

```json
{
  "data": {
    "prompt_limit": 32768,
    "shuffle_seed": 20260921
  },
  "execution": {
    "development_cases_per_task": 2,
    "max_development_structural_memory_tags": 0,
    "min_development_answer_completion": 0.9,
    "repetition_failure_span_tokens": 256,
    "workers": 1
  },
  "experiment": {
    "arms": [
      "plain_ar",
      "filtered_futures"
    ],
    "branch_tokens": 64,
    "checkpoint_body_tokens": 128,
    "commit": "selected_rollout",
    "lookahead": {
      "contradiction_penalty": 0.25,
      "margin": 0.1,
      "min_tokens": 16,
      "statistic": "mean_logprob"
    },
    "max_branch_body_tokens": 24576,
    "max_event_memory_tokens": 2048,
    "max_output_tokens": 32768,
    "memory_capacity_tokens": 8192,
    "memory_compact_to_tokens": 4096,
    "memory_preamble": "Other directions that were started here but not followed. They are unverified hypotheses and may be wrong or incomplete; treat them as hints, not conclusions. Note: verify all constraints carefully and do not assume answers must be integers unless explicitly stated.",
    "memory_quality_gate": {
      "max_score_gap": 0.1
    },
    "min_branch_interval_tokens": 256,
    "min_candidate_probability": 0.2,
    "ours_budget_forcing": {
      "answer_tokens": 2047,
      "force_at_body_tokens": 30720
    },
    "prefill_chunk_tokens": 256,
    "repetition_guard": {
      "enabled": true,
      "max_period_tokens": 32,
      "min_cycles": 4,
      "min_span_tokens": 64
    },
    "seed": 95021,
    "selection": "lookahead",
    "temperature": 0.6,
    "top_k": 20,
    "top_p": 0.95
  },
  "model": {
    "backend": "vllm",
    "cache_dir": "<MODEL_CACHE>",
    "cuda_allocator_config": "expandable_segments:True",
    "device": "cuda:0",
    "dtype": "bfloat16",
    "enable_thinking": true,
    "gpu_memory_fraction": 0.85,
    "local_files_only": true,
    "max_context_tokens": 73856,
    "name": "Qwen/Qwen3-4B-Thinking-2507",
    "revision": "768f209d9ea81521153ed38c47d515654e938aea",
    "rollout_cache_offload_threshold_tokens": 49000,
    "threads": 4,
    "vllm_batch_size": 8,
    "vllm_batch_tokens": 4096
  },
  "protocol": "recurrent-reasoning-memory-v4",
  "similarity": {
    "comparison": "retained_candidates",
    "encoder": {
      "batch_size": 8,
      "cache_dir": "<MODEL_CACHE>",
      "device": "cpu",
      "dtype": "float32",
      "local_files_only": true,
      "max_tokens": 512,
      "name": "Qwen/Qwen3-Embedding-0.6B",
      "revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    },
    "min_threshold": 0.2,
    "text_scope": "rollout_only",
    "threshold": 0.85
  }
}
```

## Source identity

```json
{
  "lost_tokens/__init__.py": "f4fafc5e33b6ba841f7e37e753004d4cfb3825e0fcf8632faf352453386e7662",
  "lost_tokens/__main__.py": "6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279",
  "lost_tokens/audit.py": "29c5ea6c1da97c166bf6dd2ea738685b14eda7240610f5116158c61641c887e0",
  "lost_tokens/backend.py": "055095ca8035d57364215757ad4df7d3ccbbedd660b2c58914781995ded2ff97",
  "lost_tokens/cli.py": "284689c9de264b78b14f904d346aefa0751202a351658657fe6d2d9cabb07a55",
  "lost_tokens/config.py": "6e8ac4124abfedd938e0eb54a40caa34c54fd007bf1a67db5acd1bf5932857d7",
  "lost_tokens/core.py": "6b90ce548bb00caab3695c858821b9764c6b40216018b81028987015833a4469",
  "lost_tokens/cosine.py": "317b38d6c2fc2e2a8a114e9bc6004197e213e32f61701db96730159c4cd97972",
  "lost_tokens/data.py": "b8faa6a53bc021882ab3cfdfb6e61b849f81e225b140f89fb238580ed1242226",
  "lost_tokens/datasets.json": "a2103b5be3d1f9d677576c74c64ecb28a11ed8ed308bdf40c46601f29c4df744",
  "lost_tokens/default.json": "d6e353e6e10cb368e0db76713ec91ec43160101ee80776848ac8e9496f1639f8",
  "lost_tokens/frozen_baseline.py": "21aa244be6e917390af5f025c104fe52a7f487eed2b3d224bd53728993f9db65",
  "lost_tokens/long_context.py": "8b85e6d425512a8b21e6a84b93328e2d1b25fb1531df09c638506b448f6eb424",
  "lost_tokens/math_scoring.py": "6831d5100dffea887ed1eaa0ec763ed48f5369d0f853ea3c9a9d66ef5e12ae2b",
  "lost_tokens/protocol.py": "41b8baf6b7559a002703272658b15c67bc8ce0ad5dc68cc91d8fe0262905445a",
  "lost_tokens/recurrent_memory.py": "fa7f6bc4b1c7e3ae5cbfa56c1e404a6f1c1c9da7a0a3a3d33001ffc5edc4db06",
  "lost_tokens/repetition.py": "6e1c9492c761a40a9c5d66b7b03f7708e26e69a247332e90f1be0c4da69a9921",
  "lost_tokens/reporting.py": "db4c26e509dc1b070699033127c37d22b9edf12ded5e31f740b06f2f4d2ea9de",
  "lost_tokens/runner.py": "a9704797b120ea402d3f537c73bd35aa1faad34361ad21e00375719390850413",
  "lost_tokens/runtime.py": "e5a61d59fca5537308812a084e5aae8567cbb749ca29fcb62b4bb221366804b1",
  "lost_tokens/vllm_backend.py": "d52251a62a64ea3384eac31cb8307e1425f5f64c5bcab2111a94630ad16b3605"
}
```

## Baseline availability

AR baseline was not measured or reused in this study. The user explicitly requested ours-only evaluation.
Report ours accuracy on the frozen cohort; do not claim a matched baseline improvement.

## Environment

See [environment.json](environment.json) and per-run
`reports/<task>/worker-environments.json` for exact GPU allocation and runtime versions.

## Results

See [summary.md](summary.md) for accuracy, missing-answer recovery, actual times and the paired comparison against previous Ours.
