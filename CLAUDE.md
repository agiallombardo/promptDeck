# promptDeck — LLM runbook

## Elevator pitch

Internal app: **HTML deck** presentations — upload `.html` / `.zip`, sandboxed iframe preview, coordinate-pinned comments (v1 = manual refresh), scoped share links, export PDF / single-file HTML. Repo tuned for agents: navigate, verify, extend safely.

## Directory map

| Path | Role |
|------|------|
| `backend/` | FastAPI (`app/main.py`), routers, Alembic, `openapi.json` |
| `frontend/` | Vite + React + TS + Tailwind 4 (`src/styles/tailwind.css` `@theme`) |
| `scripts/` | `verify.sh`, `dev.sh`, `e2e_smoke.py`, `bootstrap_users.py`, `seed.py` |
| `docs/` | Conventions, runbook, ADRs, `docs/ROADMAP.md`, `API.md` (OpenAPI) |
| `deploy/` | Samples: `systemd/promptdeck-api.service`, `nginx/promptdeck.conf.sample` (`/opt/promptDeck`, local/LAN HTTP by default) |

### Files most often modified

| Area | Paths |
|------|--------|
| HTTP API | `backend/app/routers/`, `backend/app/schemas/`, `backend/app/deps.py` |
| Auth / ACL | `backend/app/deps.py`, `backend/app/services/acl.py` |
| Frontend page | `frontend/src/pages/PresentationPage.tsx`, `frontend/src/lib/api.ts` |
| OpenAPI / types | `backend/openapi.json`, `frontend/src/lib/api/schema.d.ts` (`just api-contract`) |

## Command cheat sheet

Prereqs: **Python 3.12+**, **uv**, **Node.js Active LTS** (24.x; GitHub Actions uses `lts/*`). **pnpm 10.x** (pinned in `frontend/package.json` `packageManager`; stable line is `latest-10` on npm); `scripts/pnpm.sh` falls back to `npx pnpm@…` with that version if `pnpm` is missing.

Copy `backend/.env.example` → `backend/.env` (no secrets in git).

When upgrading **pnpm**, bump `packageManager` in `frontend/package.json` and the `npx pnpm@…` pin in `scripts/pnpm.sh`; CI reads `packageManager` via `pnpm/action-setup` (`package_json_file: frontend/package.json`).

```bash
just setup              # uv sync + pnpm install
just dev                # API :8005 + Vite :5174 (override ports via env / scripts)
just verify             # all checks (same as scripts/verify.sh)
just test-backend       # pytest
just test-frontend      # vitest run
just smoke              # in-process ASGI smoke
just lint               # ruff + frontend lint
just types              # pyright + tsc
just db-migrate         # Alembic upgrade head (Postgres); empty DB = full chain in one run — see docs/RUNBOOK.md
just api-contract       # regen `schema.d.ts` + `docs/API.md` from `backend/openapi.json`
just db-reset           # Alembic downgrade base + upgrade head + `bootstrap_users.py` + `seed.py` (destructive)
```

Optional: `pre-commit install` + `pre-commit run --all-files` (subset); full = `just verify`.

Backend one-offs:

```bash
cd backend && uv sync --group dev
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8005
cd backend && uv run python -m app.scripts.dump_openapi   # refresh openapi.json after API changes
cd backend && uv run python -m app.scripts.check_openapi_snapshot
```

## How to add X (worked deltas)

### New API route

1. **Schemas:** `backend/app/schemas/<area>.py`
2. **Router:** `backend/app/routers/<area>.py`; register in `backend/app/main.py`
3. **Tests:** `backend/tests/test_<area>.py` — happy path + one failure
4. **Contract:** `cd backend && uv run python -m app.scripts.dump_openapi`
5. **Frontend types (if API changed):** `just api-contract` → commit `frontend/src/lib/api/schema.d.ts`, `docs/API.md`
6. **Verify:** `just verify`

### New DB column

1. **Model:** `backend/app/db/models/`
2. **Migration:** `cd backend && uv run alembic revision --autogenerate -m "..."` → review `backend/alembic/versions/`
3. **Schemas:** `backend/app/schemas/`
4. **Tests:** cover field
5. **OpenAPI:** `uv run python -m app.scripts.dump_openapi` → `just api-contract` if API surface changed
6. **Verify:** `just verify`

### New frontend page

1. **Page:** `frontend/src/pages/<Name>Page.tsx`
2. **Route:** `frontend/src/router.tsx`
3. **API:** `jsonFetch` in `frontend/src/lib/api.ts` (`ApiError` + `requestId`; toasts unless `skipErrorToast`)
4. **Test:** `frontend/src/pages/<Name>Page.test.tsx` or `src/**/__tests__/`
5. **Verify:** `just verify`

### New structured log event (stdout + `app_logs`)

1. **Emit:** `channel_logger(LogChannel.<x>)` from `app/logging_channels.py`
2. **Persist:** `write_app_log` in `app/services/app_logging.py` when DB session + row needed for Admin Logs
3. **Filter:** `GET /api/v1/admin/logs?channel=` — match `LogChannel` enum
4. **Tests (optional):** `await assert_logged(session, event="your.event", level="info")` in `backend/tests/log_utils.py`
5. **Verify:** `just verify`

## Non-negotiables

- **`just verify`** before “done”.
- No hand-edit generated typings — `just api-contract` after `openapi.json` changes.
- New endpoints: schemas + router + test + `backend/openapi.json` updated.
- Prefer edit-in-place over new files when still clear.
- **File size:** No fixed LOC cap. Split when mixed concerns or unreadable — not for arbitrary number. Long cohesive file OK.

## Debugging flow (target state)

Toast **request ID** → Admin logs filter → payload → fix → regression test. (Admin UI M1+.)

## Scope

Deferred: `docs/ROADMAP.md`.
