#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Add development dependencies to the dev dependency group.
#   Updates pyproject.toml and uv.lock for tooling/test-only packages.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN15_SCRIPT_VERSION="v0.0.1"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run15_uv_add_dev.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./run15_uv_add_dev.sh <package> [package2 ...]"
    echo
    echo "Examples:"
    echo "  ./run15_uv_add_dev.sh ruff"
    echo "  ./run15_uv_add_dev.sh mypy ruff"
    exit 1
fi

cat <<EOF
========================================
      Add Dev Packages (--group dev)
========================================
Script version : $RUN15_SCRIPT_VERSION
Project root   : $(pwd)

EOF

echo "Running: uv add --group dev $*"
uv add --group dev "$@"
echo
echo "[OK] Dev dependency added successfully."
