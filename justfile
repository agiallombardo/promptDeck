# promptDeck — single entry for humans and agents (see CLAUDE.md).

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

[private]
_pnpm *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail
    ROOT="{{justfile_directory()}}"
    # shellcheck source=scripts/pnpm.sh
    source "$ROOT/scripts/pnpm.sh"
    cd "$ROOT/frontend"
    run_pnpm {{ARGS}}

default:
    @just --list

setup:
    cd backend && uv sync --group dev
    just _pnpm install
    @echo "Run: cd backend && uv run playwright install chromium"  # when PDF export lands

dev:
    bash scripts/dev.sh

verify:
    bash scripts/verify.sh

test-backend:
    cd backend && uv run pytest -q

test-frontend:
    just _pnpm run test:run

lint:
    cd backend && uv run ruff check . && uv run ruff format --check .
    just _pnpm lint

types:
    cd backend && uv run pyright
    just _pnpm tsc

db-migrate:
    cd backend && uv run alembic upgrade head

db-reset:
    cd backend && uv run alembic downgrade base && uv run alembic upgrade head && uv run python ../scripts/bootstrap_users.py && uv run python ../scripts/seed.py

api-contract:
    just _pnpm exec openapi-typescript ../backend/openapi.json -o src/lib/api/schema.d.ts
    just _pnpm exec prettier --write src/lib/api/schema.d.ts
    uv run python scripts/gen_api_md.py

smoke:
    cd backend && uv run python ../scripts/e2e_smoke.py
