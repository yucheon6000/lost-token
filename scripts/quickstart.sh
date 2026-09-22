#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

if command -v uv >/dev/null 2>&1; then
  uv_bin="$(command -v uv)"
elif [[ -x "$repo_dir/.tools/uv" ]]; then
  uv_bin="$repo_dir/.tools/uv"
else
  mkdir -p "$repo_dir/.tools"
  curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/0.12.17/install.sh \
    | env UV_UNMANAGED_INSTALL="$repo_dir/.tools" sh
  uv_bin="$repo_dir/.tools/uv"
fi

"$uv_bin" sync --frozen
exec "$uv_bin" run --frozen lost-tokens quickstart "$@"
