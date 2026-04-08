# Runbook

## Local development

1. Install **uv**, **Node 20+**, and **PostgreSQL 16** (or point `DATABASE_URL` at a hosted instance).
2. Set `DATABASE_URL` (example: `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/promptdeck`) and `JWT_SECRET_KEY` (≥ 32 random bytes in production).
3. From repo root: `just setup`, then `just db-migrate`, then `cd backend && uv run python ../scripts/seed.py` to create the default admin (`admin@example.com` / `changeme123` unless overridden by env).
4. `just dev` — API at `http://127.0.0.1:8000`, frontend at `http://127.0.0.1:5173` (Vite proxies `/api` to the API).

Automated tests use an in-memory SQLite database and do not require Postgres.

## Health checks

- API: `GET /health` → `{"status":"ok"}`.

## Verification

```bash
just verify
```

## Production (Ubuntu VM)

Step-by-step host setup (PostgreSQL 16, nginx, UFW, systemd unit for the API, graceful reloads, dev on the same machine): **`docs/UBUNTU_SERVER_SETUP.md`**.

v1 targets a single VM with systemd units and nginx (see plan milestone M7).

## Deploy artifacts (samples)

- **API process:** `deploy/systemd/promptdeck-api.service` — adjust `User`, paths, and `EnvironmentFile` (e.g. `/etc/promptdeck/api.env` with `DATABASE_URL`, `JWT_SECRET_KEY`, `STORAGE_ROOT`, `PUBLIC_APP_URL`, `CORS_ORIGINS`).
- **Reverse proxy:** `deploy/nginx/promptdeck.conf.sample` — TLS, static `frontend/dist`, proxy `/api/` and `/a/` to uvicorn on `127.0.0.1:8000`.
- **Backups:** `scripts/backup_pg.sh` — gzip `pg_dump` using `DATABASE_URL` (async URL is rewritten to `postgresql://` for libpq).

After deploy: `alembic upgrade head`, run `scripts/seed.py` once if needed, reload nginx, `systemctl restart promptdeck-api`.
