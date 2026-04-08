#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    pnpm "$@"
  else
    npx --yes pnpm@9.15.4 "$@"
  fi
}

section() {
  echo ""
  echo "===== $1 ====="
}

section "backend lint"
(cd backend && uv run ruff check . && uv run ruff format --check .)

section "backend types"
(cd backend && uv run pyright)

section "backend tests"
(cd backend && uv run pytest -q)

section "frontend lint"
(cd frontend && run_pnpm lint)

section "frontend types"
(cd frontend && run_pnpm tsc)

section "frontend unit tests"
(cd frontend && run_pnpm run test:run)

section "openapi contract"
(cd backend && uv run python -m app.scripts.check_openapi_snapshot)

section "smoke test"
(cd backend && uv run python ../scripts/e2e_smoke.py)

echo ""
echo "✅ verify passed"
