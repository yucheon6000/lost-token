# Lost Tokens repository

- Use `uv sync --frozen` and `uv run --frozen`; never install into system Python.
- The public implementation is under `src/lost_tokens/`. Keep protocol defaults in
  `default.json`, dataset revisions/URLs/hashes in `datasets.json`.
- No machine-specific directories, usernames, GPU counts, or experiment dates in
  executable code. Resolve storage from CLI options. Generated data belongs under
  the configurable work directory and must not be committed.
- Preserve reasoning-only branching, independent candidate caches, exact selected
  rollout commit, deterministic per-position seeds and memory compaction semantics.
- Keep checkpoint identity checks and immutable provenance. Do not modify code or
  configs used by a running experiment. Resume must preserve original deadlines.
- Before edits, save a snapshot under ignored `temp/snapshots/`.
- Run `uv run --frozen python -m unittest discover -s tests -v` after changes.
  GPU changes also require an explicitly allocated GPU smoke test. Check available
  GPUs first; never interfere with another run or change a shared environment.
- Verify README commands, wheel packaging and a different working directory before
  publishing changes to the quickstart or path handling.
