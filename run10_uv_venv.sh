#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:　Activate .venv
#   Create local virtual environment (.venv) using uv.
#   Run once after sync, then activate .venv for development.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN11_SCRIPT_VERSION="v0.0.1"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run11_uv_venv.sh must be executed directly, not sourced.\n' >&2
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
         uv venv - Create Virtual Env
========================================
Script version : $RUN11_SCRIPT_VERSION
Project root   : $(pwd)

EOF

echo "Running: uv venv"
uv venv
echo
echo "Done! Next step:"
echo "  source .venv/bin/activate"
echo "After activation, run:"
echo "  ./run12_app_start.sh"
