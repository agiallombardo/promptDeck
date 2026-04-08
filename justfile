# PresCollab — single entry for humans and agents (see CLAUDE.md).

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just --list

setup:
    cd backend && uv sync --group dev
    cd frontend && (command -v pnpm >/dev/null 2>&1 && pnpm install || npx --yes pnpm@9.15.4 install)
    @echo "Run: cd backend && uv run playwright install chromium"  # when PDF export lands

dev:
    bash scripts/dev.sh

verify:
    bash scripts/verify.sh

test-backend:
    cd backend && uv run pytest -q

test-frontend:
    cd frontend && (command -v pnpm >/dev/null 2>&1 && pnpm run test:run || npx --yes pnpm@9.15.4 run test:run)

lint:
    cd backend && uv run ruff check . && uv run ruff format --check .
    cd frontend && (command -v pnpm >/dev/null 2>&1 && pnpm lint || npx --yes pnpm@9.15.4 lint)

types:
    cd backend && uv run pyright
    cd frontend && (command -v pnpm >/dev/null 2>&1 && pnpm tsc || npx --yes pnpm@9.15.4 tsc)

db-migrate:
    cd backend && uv run alembic upgrade head

db-reset:
    @echo "Not implemented — M1"

api-contract:
    @echo "openapi-typescript not wired yet — run after M1+ when /api/v1 exists"

smoke:
    cd backend && uv run python ../scripts/e2e_smoke.py
