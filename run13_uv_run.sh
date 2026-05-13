#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Execute an arbitrary command through uv-managed environment.
#   Useful for one-shot commands without manual venv activation.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN13_SCRIPT_VERSION="v0.0.2"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run13_uv_run.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./run13_uv_run.sh <command> [args ...]"
    echo
    echo "Examples:"
    echo "  ./run13_uv_run.sh python -m pip list"
    echo "  ./run13_uv_run.sh pytest tests/test_phase1_api.py -v"
    exit 1
fi

cat <<EOF
========================================
           uv run passthrough
========================================
Script version : $RUN13_SCRIPT_VERSION
Project root   : $(pwd)

EOF

echo "Running: uv run $*"
uv run "$@"
echo
echo "[OK] uv run command completed successfully."
