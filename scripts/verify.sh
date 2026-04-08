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

section "frontend api contract (generated TS + API.md)"
(cd frontend && run_pnpm exec openapi-typescript ../backend/openapi.json -o src/lib/api/schema.d.ts)
(cd frontend && run_pnpm exec prettier --write src/lib/api/schema.d.ts)
(cd "$ROOT" && uv run python scripts/gen_api_md.py)
contract_check() {
  local path="$1"
  if ! git cat-file -e "HEAD:${path}" 2>/dev/null; then
    echo "FAIL: ${path} is missing from the last commit — run \`just api-contract\` and commit it"
    exit 1
  fi
  local wt committed
  wt=$(git hash-object "${path}")
  committed=$(git rev-parse "HEAD:${path}")
  if [ "${wt}" != "${committed}" ]; then
    echo "FAIL: ${path} out of date vs git HEAD — run \`just api-contract\` and commit"
    exit 1
  fi
}
contract_check frontend/src/lib/api/schema.d.ts
contract_check docs/API.md

section "smoke test"
(cd backend && uv run python ../scripts/e2e_smoke.py)

echo ""
echo "✅ verify passed"
