#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trap 'kill 0' EXIT
# shellcheck source=pnpm.sh
source "$ROOT/scripts/pnpm.sh"

(cd "$ROOT/backend" && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8005) &
(cd "$ROOT/frontend" && run_pnpm dev) &
wait
