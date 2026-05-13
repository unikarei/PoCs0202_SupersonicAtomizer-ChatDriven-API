#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Add runtime (production) dependencies required by the application.
#   Updates pyproject.toml and uv.lock for deploy/runtime packages.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN16_SCRIPT_VERSION="v0.0.1"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run16_uv_add_prd.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./run16_uv_add_prd.sh <package> [package2 ...]"
    echo
    echo "Examples:"
    echo "  ./run16_uv_add_prd.sh numpy"
    echo "  ./run16_uv_add_prd.sh numpy scipy"
    exit 1
fi

cat <<EOF
========================================
        Add Production Packages
========================================
Script version : $RUN16_SCRIPT_VERSION
Project root   : $(pwd)

EOF

echo "Running: uv add $*"
uv add "$@"
echo
echo "[OK] Runtime dependency added successfully."
