# Conventions

## Layers

- **Routers** validate HTTP and call **services**; services own business logic and use the DB/repos.
- **Pydantic** models at boundaries: `*Create`, `*Read`, `*Update` where applicable.
- **Errors:** Prefer structured problem responses (to be standardized in M1+).

## Typing

- Python: annotate public functions; avoid untyped `dict` at API boundaries.
- TypeScript: `strict` mode; no `any` at component props or API DTOs.

## Tests

- Backend: `pytest` + `httpx.AsyncClient` + ASGI transport; one test module per router area when routers exist.
- Frontend: Vitest + Testing Library; colocate `*.test.tsx` next to components or under `src/`.

## Formatting

- Python: `ruff format` + `ruff check`.
- Frontend: Prettier + ESLint (flat config).

## Logging channels

Structured logs use a **channel** (stored in `app_logs.logger`, JSON field `channel` in API):

| Channel | Meaning |
|--------|---------|
| `http` | ASGI request/response (middleware) |
| `auth` | Login, refresh, logout outcomes |
| `audit` | Security-sensitive actions (e.g. admin viewing logs) |
| `script` | CLI entrypoints (`scripts/bootstrap_users.py`, `scripts/seed.py`, `e2e_smoke.py`) |

Structlog logger names are `app.<channel>`; stdout JSON includes `channel` when bound or derived from the logger name.
