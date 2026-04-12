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

## Docker deployment (SQLite, all-in-one)

Optional **single container**: FastAPI + **file-backed SQLite** on a Docker volume, built **Vite UI** served from the API (same origin as `/api/v1`), and **Playwright Chromium** baked in for PDF/HTML export. Image is **large** (~Chromium); use **PostgreSQL + systemd + nginx** ([§ Production](#production-ubuntu-vm), `docs/UBUNTU_SERVER_SETUP.md`, `deploy/`) for normal production.

1. **Prerequisites:** Docker Engine and Compose v2, several GB disk for the image, host port **8080** free (or edit `ports` in root `docker-compose.yml`).
2. **Secrets:** set a long `JWT_SECRET_KEY` (≥ 32 random bytes). Example: `export JWT_SECRET_KEY=$(openssl rand -hex 32)` or copy `deploy/docker-compose.env.example` to `.env` beside `docker-compose.yml` and edit.
3. **Build:** from repo root, `docker compose build`, or `just docker-build`.
4. **Run:** `docker compose up -d`, or `just docker-up` (ensure `JWT_SECRET_KEY` is set in the environment or via `.env` next to the compose file). The entrypoint runs **`alembic upgrade head`** on each start, then **uvicorn** on port **8005** inside the container (mapped to **8080** on the host by default).
5. **Environment (in compose):**
   - `DATABASE_URL=sqlite+aiosqlite:////data/promptdeck.db` — four slashes after the scheme mean an **absolute path** inside the container; data lives on the **`promptdeck-data`** named volume mounted at `/data`.
   - `STORAGE_ROOT=/data/storage` — uploaded decks and exports.
   - `STATIC_SITE_DIR=/app/backend/static/site` — baked-in Vite production build.
   - `PUBLIC_APP_URL` and `PUBLIC_API_URL` must be the **exact origin** users type in the browser (e.g. `http://127.0.0.1:8080`). Same-origin avoids extra frontend env vars.
   - `CORS_ORIGINS` — JSON array of allowed origins; **must include** that same origin (see default in `docker-compose.yml`).
   - Optional: `ASSET_SIGNING_KEY` is **not** used by the app (asset URLs use `JWT_SECRET_KEY`); you can ignore legacy `.env` examples mentioning it.
6. **First admin user:** migrations run automatically; create logins once:

   ```bash
   docker compose exec -w /app/backend promptdeck uv run python /app/scripts/bootstrap_users.py
   ```

   Defaults match local dev (`admin@example.com` / `changeme123`, etc.); override with `BOOTSTRAP_*` env on that command if needed.

7. **Verify:** open `http://127.0.0.1:8080` (or your chosen origin), confirm `GET http://127.0.0.1:8080/health` returns `{"status":"ok"}`, sign in, and exercise uploads/exports (export needs Chromium in the image).
8. **Microsoft Entra (OAuth):** register redirect URI **`{PUBLIC_API_URL}/api/v1/auth/entra/callback`** in Entra (same string shown under Admin → Identity / Entra). Set `ENTRA_*` variables (see `backend/.env.example`) and enable in Admin or via env. Use **`COOKIE_SECURE=true`** when the app is served over **HTTPS** (reverse proxy or TLS at the edge). Helper: `scripts/azure-entra-app-registration.sh`.
9. **Upgrades:** `git pull`, `docker compose build`, `docker compose up -d` (migrations apply on container start).
10. **Backups:** copy the named volume’s contents (`promptdeck.db` under `/data` and files under `/data/storage`) or use `docker run --rm -v promptdeck-data:/data …` to archive `/data`.

## Production (Ubuntu VM)

Step-by-step host setup (PostgreSQL 18, nginx, UFW, systemd unit for the API, graceful reloads, dev on the same machine): **`docs/UBUNTU_SERVER_SETUP.md`**.

Targets a **local or LAN** machine (no public domain): users open something like **`http://192.168.x.x`** or **`http://hostname.local`**. Set **`PUBLIC_APP_URL`** and **`CORS_ORIGINS`** to that exact origin; use **`COOKIE_SECURE=false`** with plain HTTP. Deployed checkout: **`/opt/promptDeck`** (see `deploy/` samples).

## Deploy artifacts (samples)

- **API process:** `deploy/systemd/promptdeck-api.service` — expects repo at `/opt/promptDeck`; adjust `User`, `WorkingDirectory`, and `EnvironmentFile` (e.g. `/etc/promptdeck/.env` with `DATABASE_URL`, `JWT_SECRET_KEY`, `STORAGE_ROOT`, `PUBLIC_APP_URL`, `CORS_ORIGINS`).
- **Reverse proxy:** `deploy/nginx/promptdeck.conf.sample` — port **80** redirects to **HTTPS** on **443** (self-signed or real certs); static files and `/api/` + `/a/` proxies on 443 only. Plain HTTP-only nginx: see **`docs/UBUNTU_SERVER_SETUP.md` §3.2**. LAN **IP** + self-signed: **§3.3** (cert SAN + `PUBLIC_APP_URL` / `CORS_ORIGINS` / `COOKIE_SECURE`).
- **Backups:** `scripts/backup_pg.sh` — gzip `pg_dump` using `DATABASE_URL` (async URL is rewritten to `postgresql://` for libpq).

After deploy: `alembic upgrade head` (same as `just db-migrate` from `backend/`; on a **fresh** DB this one pass creates the full schema). Run `scripts/bootstrap_users.py` once if you need initial login accounts (not the editor unless `ENVIRONMENT=development` or `BOOTSTRAP_DEMO_USERS=1`). Use `scripts/seed.py` only for application data seeding (currently a no-op). Reload nginx, `systemctl restart promptdeck-api`.

**Note:** Initial users used to be created via `SEED_ADMIN_*` and `scripts/seed.py`. That is replaced by `BOOTSTRAP_ADMIN_*` / `BOOTSTRAP_EDITOR_*` and `scripts/bootstrap_users.py`. Update any saved `.env` keys accordingly.
