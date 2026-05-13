#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose: Update dependencies.
#   Synchronize project dependencies from pyproject.toml/uv.lock into local env.
#   Use this first when setting up or after dependency changes.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN10_SCRIPT_VERSION="v0.0.2"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
	printf 'Error: run10_uv_sync.sh must be executed directly, not sourced.\n' >&2
	return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v uv >/dev/null 2>&1; then
	echo "[Error] uv is not installed or not in PATH." >&2
	echo "        Install uv first: https://docs.astral.sh/uv/" >&2
	exit 1
fi

cat <<EOF
========================================
			 uv sync Script
========================================
Script version : $RUN10_SCRIPT_VERSION
Project root   : $(pwd)

EOF

echo "Running: uv sync"
uv sync
echo
echo "[OK] uv sync completed successfully."
