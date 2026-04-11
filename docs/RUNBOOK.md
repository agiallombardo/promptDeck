# Runbook

## Local development

1. Install **uv**, **Node.js Active LTS** (24.x line; CI uses `lts/*`), and **PostgreSQL 18** (or point `DATABASE_URL` at a hosted instance).
2. Set `DATABASE_URL` (example: `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/promptdeck`) and `JWT_SECRET_KEY` (≥ 32 random bytes in production).
3. From repo root: `just setup`, then `just db-migrate`, then `cd backend && uv run python ../scripts/bootstrap_users.py` to create login users. Defaults: admin `admin@example.com` / `changeme123`, and in **development** an editor `editor@example.com` / `changeme123` (override with `BOOTSTRAP_*` env vars). Set `BOOTSTRAP_DEMO_USERS=0` to create only the admin, or `BOOTSTRAP_DEMO_USERS=1` to force the editor in any environment.
4. `just dev` — API at `http://127.0.0.1:8005`, frontend at `http://127.0.0.1:5174` by default (Vite proxies `/api` to the API). If a port is busy, adjust `VITE_DEV_PORT` / uvicorn `--port` and align `CORS_ORIGINS` / `PUBLIC_APP_URL` in backend `.env` if needed.

**Database schema:** `just db-migrate` runs `alembic upgrade head`. On a **new, empty** Postgres database, that single command applies the **entire** revision chain (all tables, including e.g. `audit_log`)—there are no separate per-feature migration steps. After `git pull` when new files appear under `backend/alembic/versions/`, run `just db-migrate` again.

Automated tests use an in-memory SQLite database and do not require Postgres.

## Health checks

- API: `GET /health` → `{"status":"ok"}`.

## Verification

```bash
just verify
```

## Production (Ubuntu VM)

Step-by-step host setup (PostgreSQL 18, nginx, UFW, systemd unit for the API, graceful reloads, dev on the same machine): **`docs/UBUNTU_SERVER_SETUP.md`**.

Targets a **local or LAN** machine (no public domain): users open something like **`http://192.168.x.x`** or **`http://hostname.local`**. Set **`PUBLIC_APP_URL`** and **`CORS_ORIGINS`** to that exact origin; use **`COOKIE_SECURE=false`** with plain HTTP. Deployed checkout: **`/opt/promptDeck`** (see `deploy/` samples).

## Deploy artifacts (samples)

- **API process:** `deploy/systemd/promptdeck-api.service` — expects repo at `/opt/promptDeck`; adjust `User`, `WorkingDirectory`, and `EnvironmentFile` (e.g. `/etc/promptdeck/.env` with `DATABASE_URL`, `JWT_SECRET_KEY`, `STORAGE_ROOT`, `PUBLIC_APP_URL`, `CORS_ORIGINS`).
- **Reverse proxy:** `deploy/nginx/promptdeck.conf.sample` — port **80** redirects to **HTTPS** on **443** (self-signed or real certs); static files and `/api/` + `/a/` proxies on 443 only. Plain HTTP-only nginx: see **`docs/UBUNTU_SERVER_SETUP.md` §3.2**. LAN **IP** + self-signed: **§3.3** (cert SAN + `PUBLIC_APP_URL` / `CORS_ORIGINS` / `COOKIE_SECURE`).
- **Backups:** `scripts/backup_pg.sh` — gzip `pg_dump` using `DATABASE_URL` (async URL is rewritten to `postgresql://` for libpq).

After deploy: `alembic upgrade head` (same as `just db-migrate` from `backend/`; on a **fresh** DB this one pass creates the full schema). Run `scripts/bootstrap_users.py` once if you need initial login accounts (not the editor unless `ENVIRONMENT=development` or `BOOTSTRAP_DEMO_USERS=1`). Use `scripts/seed.py` only for application data seeding (currently a no-op). Reload nginx, `systemctl restart promptdeck-api`.

**Note:** Initial users used to be created via `SEED_ADMIN_*` and `scripts/seed.py`. That is replaced by `BOOTSTRAP_ADMIN_*` / `BOOTSTRAP_EDITOR_*` and `scripts/bootstrap_users.py`. Update any saved `.env` keys accordingly.
