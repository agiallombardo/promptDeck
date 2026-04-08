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
| `docs/` | Conventions, runbook, ADRs, roadmap, `API.md` (generated from OpenAPI) |
| `deploy/` | Reserved for systemd/nginx (M7) |

### Files most often modified

| Area | Paths |
|------|--------|
| HTTP API | `backend/app/routers/`, `backend/app/schemas/`, `backend/app/deps.py` |
| Auth / ACL | `backend/app/deps.py`, `backend/app/services/acl.py` |
| Frontend page | `frontend/src/pages/PresentationPage.tsx`, `frontend/src/lib/api.ts` |
| OpenAPI / types | `backend/openapi.json`, `frontend/src/lib/api/schema.d.ts` (run `just api-contract`) |

## Command cheat sheet

Prereqs: **Python 3.12+**, **uv**, **Node 20+** (use `pnpm` globally or `npx pnpm@9.15.4` — `scripts/verify.sh` falls back automatically).

Local env template: `backend/.env.example` (copy to `backend/.env`; never commit secrets).

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
just api-contract       # regen `schema.d.ts` + `docs/API.md` from `backend/openapi.json`
just db-reset           # Alembic downgrade base + upgrade head + `scripts/seed.py` (destructive)
```

Optional: `pre-commit install` then `pre-commit run --all-files` (ruff + prettier; full suite is `just verify`).

Backend one-offs:

```bash
cd backend && uv sync --group dev
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd backend && uv run python -m app.scripts.dump_openapi   # refresh openapi.json after API changes
cd backend && uv run python -m app.scripts.check_openapi_snapshot
```

## How to add X (worked deltas)

### New API route

1. **Schemas:** add or extend Pydantic models in `backend/app/schemas/<area>.py`.
2. **Router:** add handlers in `backend/app/routers/<area>.py` (or new module); register the router in `backend/app/main.py`.
3. **Tests:** add `backend/tests/test_<area>.py` (or extend an existing file) covering happy path + one failure mode.
4. **Contract:** `cd backend && uv run python -m app.scripts.dump_openapi`
5. **Frontend types (if API shape changed):** `just api-contract` then commit `frontend/src/lib/api/schema.d.ts` and `docs/API.md`.
6. **Verify:** `just verify`

### New DB column

1. **Model:** edit the SQLAlchemy model under `backend/app/db/models/`.
2. **Migration:** `cd backend && uv run alembic revision --autogenerate -m "..."` then review the file under `backend/alembic/versions/`.
3. **Schemas:** update Pydantic read/write models in `backend/app/schemas/`.
4. **Tests:** extend a test that exercises the field.
5. **OpenAPI:** `uv run python -m app.scripts.dump_openapi` → `just api-contract` if the API surface changed.
6. **Verify:** `just verify`

### New frontend page

1. **Page component:** `frontend/src/pages/<Name>Page.tsx`.
2. **Route:** add a `<Route>` in `frontend/src/router.tsx`.
3. **API calls:** prefer `jsonFetch` patterns in `frontend/src/lib/api.ts` (throws `ApiError` with `requestId`; toasts fire unless `skipErrorToast`).
4. **Test:** colocate `frontend/src/pages/<Name>Page.test.tsx` or under `src/**/__tests__/` mirroring existing Vitest layout.
5. **Verify:** `just verify`

### New structured log event (stdout + `app_logs`)

1. **Emit:** use the appropriate `channel_logger(LogChannel.<x>)` from `app/logging_channels.py` in the code path.
2. **Persist:** call `write_app_log` from `app/services/app_logging.py` where the request has a DB session and you need a row for Admin Logs.
3. **Filter:** Admin UI uses `GET /api/v1/admin/logs?channel=` — values must match `LogChannel` enum.
4. **Tests (optional):** `await assert_logged(session, event="your.event", level="info")` via `backend/tests/log_utils.py`.
5. **Verify:** `just verify`

## Non-negotiables

- Run **`just verify`** before claiming work is done.
- Do **not** hand-edit generated API typings — regenerate with **`just api-contract`** after `openapi.json` changes.
- New endpoints: schemas + router + test + updated `backend/openapi.json`.
- Prefer editing existing files over adding new ones when it stays clear.
- **File size:** There is no fixed line-count target (e.g. 300 or 400 LOC). Split or extract modules when a file mixes unrelated concerns or becomes hard to follow — not to hit an arbitrary cap. If one cohesive unit reads well at a higher length, that is fine.

## Debugging flow (target state)

User copies **request ID** from a toast → Admin logs filter → inspect payload → fix → regression test. Admin UI arrives in M1+.

## Scope

Deferred items and rationale: `docs/ROADMAP.md`. Full v1 spec: `plans/humming-bouncing-toast.md`.
