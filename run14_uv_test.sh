#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Run project tests through uv-managed environment.
#   Defaults to tests/ with verbose output, or passes custom pytest args.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN14_SCRIPT_VERSION="v0.0.2"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
	printf 'Error: run14_uv_test.sh must be executed directly, not sourced.\n' >&2
	return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1

if ! command -v uv >/dev/null 2>&1; then
	echo "[Error] uv is not installed or not in PATH." >&2
	exit 1
fi

cat <<EOF
========================================
			Run Tests with uv
========================================
Script version : $RUN14_SCRIPT_VERSION
Project root   : $(pwd)

EOF

if [ $# -eq 0 ]; then
	echo "Running: uv run pytest tests/ -v"
	uv run pytest tests/ -v
else
	echo "Running: uv run pytest $*"
	uv run pytest "$@"
fi

echo
echo "[OK] Test command completed successfully."
