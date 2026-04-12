# promptDeck

Internal web app for **HTML slide decks**: upload `.html` or `.zip`, preview in a sandboxed iframe, add coordinate-pinned comments, share via scoped links, and export to PDF or a single-file HTML bundle.

## Features

- **Deck authoring** — Single-file HTML or zipped bundles with an entry HTML file.
- **Collaboration** — Comment threads pinned to slide coordinates (refresh to see updates in v1).
- **Sharing** — Time- or scope-limited share links.
- **Export** — PDF and self-contained HTML output paths.
- **Ops-friendly** — FastAPI + Postgres by default; sample systemd/nginx under `deploy/`. Optional **Docker** all-in-one (SQLite + static UI + Chromium for export) is documented in **`docs/RUNBOOK.md`**.

## Stack

| Layer    | Technology                                      |
| -------- | ----------------------------------------------- |
| API      | Python 3.12+, FastAPI, SQLAlchemy, Alembic, uv  |
| Frontend | Vite, React, TypeScript, Tailwind CSS 4, pnpm 10 |
| Database | PostgreSQL (recommended production); SQLite optional in Docker; in-memory SQLite in tests |

## Quick start

1. Install **uv**, **Node.js** (Active LTS; see `frontend/package.json` / `.nvmrc`), and **PostgreSQL**.
2. Copy `backend/.env.example` → `backend/.env` and set `DATABASE_URL`, `JWT_SECRET_KEY`, and related vars.
3. From the repo root:

   ```bash
   just setup
   just db-migrate
   cd backend && uv run python ../scripts/bootstrap_users.py
   just dev
   ```

   Defaults: API `http://127.0.0.1:8005`, frontend `http://127.0.0.1:5174` (Vite proxies `/api`).

Full setup, production notes, and verification: **`docs/RUNBOOK.md`**.

## Deployment

- **Typical production:** PostgreSQL, `just db-migrate`, `scripts/bootstrap_users.py`, API behind nginx — see **`docs/RUNBOOK.md`** and step-by-step **`docs/UBUNTU_SERVER_SETUP.md`** (with `deploy/` samples).
- **Optional single container:** Docker Compose with SQLite on a volume, same-origin UI, and Playwright for exports — numbered steps in **`docs/RUNBOOK.md`** (section *Docker deployment*). Example env: **`deploy/docker-compose.env.example`**.

## Development

```bash
just verify    # lint, types, tests, OpenAPI checks, smoke (same as scripts/verify.sh)
just test-backend
just test-frontend
```

After HTTP API changes, refresh the OpenAPI snapshot and client contract:

```bash
cd backend && uv run python -m app.scripts.dump_openapi
just api-contract
```

Agent-oriented conventions and file map: **`CLAUDE.md`** / **`AGENTS.md`**.

## License

Copyright © 2025–2026 Anthony Giallombardo, NullQu LLC.

Licensed under the **GNU General Public License v3.0**. See [`LICENSE`](LICENSE) for the full text.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
