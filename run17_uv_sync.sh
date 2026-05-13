#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Compatibility wrapper for dependency synchronization.
#   Delegates to run11_uv_sync.sh so teams/scripts can use run17 uniformly.
# ------------------------------------------------------------------------------
set -euo pipefail

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run17_uv_sync.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$ROOT/run11_uv_sync.sh"

cd "$ROOT" || exit 1

if [ ! -f "$TARGET" ]; then
    echo "[Error] Target script not found: $TARGET" >&2
    exit 1
fi

cat <<EOF
========================================
       run17 wrapper - uv sync
========================================
Delegating to: run11_uv_sync.sh

EOF

bash "$TARGET"
