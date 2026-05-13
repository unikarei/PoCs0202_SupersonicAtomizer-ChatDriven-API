#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose: Start FastAPI server
#   Start FastAPI development server (uvicorn with --reload) for this project.
#   Intended as the primary local app startup entry point.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN12_SCRIPT_VERSION="v0.0.1"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run12_app_start.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/src"
UVICORN_HOST="127.0.0.1"
UVICORN_PORT="8000"

cd "$ROOT" || exit 1

if [ ! -d "$ROOT/src" ]; then
    echo "[Error] src directory not found: $ROOT/src" >&2
    exit 1
fi

cat <<EOF
========================================
     Start Supersonic Atomizer OptByAPI
========================================
Script version : $RUN12_SCRIPT_VERSION
Root           : $ROOT
PYTHONPATH     : $PYTHONPATH
URL            : http://$UVICORN_HOST:$UVICORN_PORT/

EOF

echo "Running FastAPI app with auto-reload..."
python -m uvicorn supersonic_atomizer_optbyapi.api.app:app --reload --host "$UVICORN_HOST" --port "$UVICORN_PORT"
