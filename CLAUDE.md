# promptDeck — LLM runbook

## Elevator pitch

promptDeck is an internal web app for **HTML “deck” presentations**: upload `.html` or `.zip`, preview in a sandboxed iframe, leave coordinate-pinned comments (manual refresh in v1), share scoped links, and export to PDF or single-file HTML. This repo is optimized so coding agents can navigate, verify, and extend it safely.

## Directory map

| Path | Role |
|------|------|
| `backend/` | FastAPI app (`app/main.py`), future routers, Alembic, `openapi.json` snapshot |
| `frontend/` | Vite + React + TypeScript + Tailwind 4 (`src/styles/tailwind.css` `@theme`) |
| `scripts/` | `verify.sh` (all checks), `dev.sh` (API + Vite), `e2e_smoke.py`, `seed.py` (admin user) |
| `plans/` | Product/implementation plans (source of truth for milestones) |
| `docs/` | Conventions, runbook, ADRs, roadmap |
| `deploy/` | Reserved for systemd/nginx (M7) |

## Command cheat sheet

Prereqs: **Python 3.12+**, **uv**, **Node 20+** (use `pnpm` globally or `npx pnpm@9.15.4` — `scripts/verify.sh` falls back automatically).

```bash
just setup              # uv sync + pnpm install
just dev                # API :8000 + Vite :5173
just verify             # all checks (same as scripts/verify.sh)
just test-backend       # pytest
just test-frontend      # vitest run
just smoke              # in-process ASGI smoke
just lint               # ruff + frontend lint
just types              # pyright + tsc
just db-migrate         # Alembic upgrade head (Postgres)
```

Backend one-offs:

```bash
cd backend && uv sync --group dev
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd backend && uv run python -m app.scripts.dump_openapi   # refresh openapi.json after API changes
cd backend && uv run python -m app.scripts.check_openapi_snapshot
```

## How to add X (recipes)

- **New API route:** `backend/app/routers/` (when introduced) + Pydantic schemas + test under `backend/tests/` + `uv run python -m app.scripts.dump_openapi` + `just verify`.
- **New DB field:** Alembic migration (M1+) + model + schema + test.
- **New frontend page:** `frontend/src/pages/` + router (when added) + test alongside.
- **New log event (later):** structlog event + `app_logs` row + Admin UI filter.

## Non-negotiables

- Run **`just verify`** before claiming work is done.
- Do **not** hand-edit generated API clients when they exist; regenerate from OpenAPI (wired in a later milestone).
- New endpoints: schemas + router + test + updated `openapi.json`.
- Prefer editing existing files over adding new ones; keep files under ~400 LOC where practical.

## Debugging flow (target state)

User copies **request ID** from a toast → Admin logs filter → inspect payload → fix → regression test. Admin UI arrives in M1+.

## Scope

Deferred items and rationale: `docs/ROADMAP.md`. Full v1 spec: `plans/humming-bouncing-toast.md`.
