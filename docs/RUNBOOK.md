# Runbook

## Local development

1. Install **uv**, **Node 20+**, and **PostgreSQL 16** (or point `DATABASE_URL` at a hosted instance).
2. Set `DATABASE_URL` (example: `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/promptdeck`) and `JWT_SECRET_KEY` (≥ 32 random bytes in production).
3. From repo root: `just setup`, then `just db-migrate`, then `cd backend && uv run python ../scripts/seed.py` to create the default admin (`admin@example.com` / `changeme123` unless overridden by env).
4. `just dev` — API at `http://127.0.0.1:8005`, frontend at `http://127.0.0.1:5174` by default (Vite proxies `/api` to the API). If a port is busy, adjust `VITE_DEV_PORT` / uvicorn `--port` and align `CORS_ORIGINS` / `PUBLIC_APP_URL` in backend `.env` if needed.
5. **Docker (`just docker-up`):** Compose uses the **default bridge network** (NAT outbound to the internet). Postgres and API listen on **`0.0.0.0` inside the container** so other services can reach them; published ports are bound to **`127.0.0.1`** on the host (`POSTGRES_PORT`, `API_PORT`, `FRONTEND_PORT` can override defaults 5432 / 8005 / 5174—use another `POSTGRES_PORT` if something else already uses 5432). **Persistence** is **Docker named volumes** (`promptdeck_postgres_data`, `promptdeck_backend_storage`), not bind mounts—data stays with the engine, separate from the repo and from a host or other-container Postgres. Inspect with `docker volume ls`; remove with `docker compose down -v` (destructive).

**Database schema:** `just db-migrate` runs `alembic upgrade head`. On a **new, empty** Postgres database, that single command applies the **entire** revision chain (all tables, including e.g. `audit_log`)—there are no separate per-feature migration steps. After `git pull` when new files appear under `backend/alembic/versions/`, run `just db-migrate` again.

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
- **Reverse proxy:** `deploy/nginx/promptdeck.conf.sample` — TLS, static `frontend/dist`, proxy `/api/` and `/a/` to uvicorn on `127.0.0.1:8005`.
- **Backups:** `scripts/backup_pg.sh` — gzip `pg_dump` using `DATABASE_URL` (async URL is rewritten to `postgresql://` for libpq).

After deploy: `alembic upgrade head` (same as `just db-migrate` from `backend/`; on a **fresh** DB this one pass creates the full schema). Run `scripts/seed.py` once if you need the default admin, reload nginx, `systemctl restart promptdeck-api`.
