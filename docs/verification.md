# Release verification

This page records the original release checks. For the current sparse profile,
see [latest changes and pending validation](latest_changes_and_validation.ko.md).

The portable package was checked locally before publication. These checks validate
installation and execution, not the scientific efficacy of the method.

| Check | Result |
|---|---|
| Frozen `uv` dependency resolution and local environment | Passed |
| Bootstrap installation when `uv` is absent | Passed; installed only into `.tools/` |
| CPU unit and protocol regression tests | 54 passed |
| Python formatting and undefined-name checks | Passed |
| Source wheel/sdist build | Passed |
| Installed wheel in a separate environment and working directory | Passed; both bundled JSON assets available |
| Original inference function/class AST comparison | Unchanged for generator backend, recurrent decoding, cosine filtering, repetition guard |
| Two-GPU quickstart, deliberate checkpoint interruption/resume | Passed |
| Four-GPU quickstart on AIME25 and GPQA | 8 paired questions; all 8 worker audits passed |
| Four-GPU recovery checkpoint preservation | 16 saved checkpoints reused without modification |
| Single-GPU regular evaluation loop, capped short generation | Both arms completed and audited |
| Short timed baseline/ours execution | Both phases stopped and partial-ledger audits passed |
| Resume of a completed run | Returned without starting new workers |
| Pinned raw downloads for all five datasets | SHA256 verified |
| Original server path scan of tracked files | No original server paths found |

The GPU smoke tests use short generation limits and their scores are intentionally
not benchmark results. Run `lost-tokens smoke` after moving to different hardware.
GPU/runtime changes can change floating-point behavior even with pinned model and
dependency versions. New worker identities record the actual runtime.

The GitHub Actions workflow repeats CPU tests, formatting checks, and package
building. It does not assume access to GPUs or benchmark/model downloads.

All complete source datasets were also normalized and hash-validated:

| Dataset | Rows | Maximum prepared prompt tokens | Truncated contexts |
|---|---:|---:|---:|
| aime25 | 30 | 796 | 0 |
| hmmt25 | 30 | 653 | 0 |
| gpqa | 448 | 2,797 | 0 |
| supergpqa | 26,529 | 4,108 | 0 |
| longbench_v2 | 503 | 32,738 | 387 |
