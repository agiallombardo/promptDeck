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

Optional **single-container** layout: API + **file-backed SQLite** on a Docker volume, production **Vite** assets served from the API (same origin as `/api/v1`), and **Playwright Chromium** in the image for PDF/HTML export. The image is **large** (Chromium). For normal production, prefer **PostgreSQL + systemd + nginx** ([§ Production (Ubuntu VM)](#production-ubuntu-vm), **`docs/UBUNTU_SERVER_SETUP.md`**, and samples under **`deploy/`**).

**Repository files (when using this layout):** root **`Dockerfile`**, root **`docker-compose.yml`**, **`scripts/docker-entrypoint.sh`**, and **`deploy/docker-compose.env.example`** (copy or adapt for secrets). If your checkout does not include the Docker assets yet, use the **Postgres + systemd + nginx** path above or merge the branch that adds them.

1. **Prerequisites:** Docker Engine and **Compose v2**, several gigabytes free disk for the image and layers, and a free host port (default compose mapping **8080→8005** inside the container). Adjust `ports` in `docker-compose.yml` if 8080 is taken.

2. **Secrets:** set **`JWT_SECRET_KEY`** to at least 32 random bytes (production). Example: `export JWT_SECRET_KEY=$(openssl rand -hex 32)`. Compose may require this variable to be set before `up` (see `docker-compose.yml`). Optionally copy **`deploy/docker-compose.env.example`** to **`.env`** next to `docker-compose.yml` and edit—do not commit real secrets.

3. **Build:** from the **repository root**, run **`docker compose build`**.

4. **Run:** **`docker compose up -d`**. The entrypoint should run **`alembic upgrade head`** on each container start, then **uvicorn** listening on **8005** inside the container.

5. **Environment (compose):** align these with your public URL:
   - **`DATABASE_URL`** — typically `sqlite+aiosqlite:////data/promptdeck.db` (four slashes after the scheme = **absolute path** inside the container).
   - **`STORAGE_ROOT`** — e.g. `/data/storage` for uploads and export artifacts; must live on a **persistent volume** with the DB.
   - **`STATIC_SITE_DIR`** — path to the baked **Vite `dist`** inside the image (e.g. `/app/backend/static/site`) so the UI and API share one origin.
   - **`PUBLIC_APP_URL`** and **`PUBLIC_API_URL`** — the **exact origin** users use in the browser (scheme + host + port), e.g. `http://127.0.0.1:8080` for local compose.
   - **`CORS_ORIGINS`** — JSON array of allowed origins; **must include** the same origin as `PUBLIC_APP_URL` (see the default in `docker-compose.yml` and override when you change the URL).
   - Optional **`ENTRA_*`**, **`COOKIE_SECURE`**, **`ENVIRONMENT`**, **`LOCAL_PASSWORD_AUTH_ENABLED`** — same semantics as **`backend/.env.example`**.

6. **Volumes:** use a **named volume** (or bind mount) mounted at **`/data`** so **`promptdeck.db`** and **`STORAGE_ROOT`** survive container recreation. Back up this volume for disaster recovery (see step 10).

7. **First admin user:** after the first successful start, create login users once (paths assume the standard image layout):

   ```bash
   docker compose exec -w /app/backend <service_name> uv run python /app/scripts/bootstrap_users.py
   ```

   Replace `<service_name>` with the service name from `docker-compose.yml` (often `promptdeck`). Defaults match local dev (`admin@example.com` / `changeme123`, etc.); override with **`BOOTSTRAP_*`** env on that command if needed.

8. **Health and smoke checks:** **`GET /health`** on the public origin should return `{"status":"ok"}`. Open the same origin in a browser, sign in, upload a deck, and run an **export** once—exports require **Chromium** in the image (**Playwright** install at build time).

9. **Upgrades:** `git pull`, **`docker compose build`**, **`docker compose up -d`**. Migrations run on container start via the entrypoint.

10. **Backups (SQLite + files):** archive the **`/data`** tree (database file under `/data` and files under **`STORAGE_ROOT`**). With a named volume, use a temporary container, e.g. `docker run --rm -v <volume_name>:/data -v $(pwd):/backup alpine tar czf /backup/promptdeck-data.tgz -C /data .` (adjust volume name and paths to match your setup).

11. **Playwright / image size:** the **Dockerfile** should run **`playwright install-deps chromium`** (or equivalent OS packages) and **`playwright install chromium`** after installing Python dependencies so headless export works. Expect a **large** image; this is intentional for in-container export.

12. **Microsoft Entra (OAuth) and TLS checklist:**
    - Register redirect URI **`{PUBLIC_API_URL}/api/v1/auth/entra/callback`** in Entra (must match **`Settings`** / Admin UI; not derived from the request `Host`). Helper: **`scripts/azure-entra-app-registration.sh`**.
    - Set **`ENTRA_TENANT_ID`**, **`ENTRA_CLIENT_ID`**, **`ENTRA_CLIENT_SECRET`**, and enable Entra in Admin or via env; optional **`ENTRA_TOKEN_ENCRYPTION_KEY`** / **`ENTRA_AUTHORITY_HOST`** per **`backend/.env.example`**.
    - When users reach the app over **HTTPS** (reverse proxy or TLS at the edge), set **`PUBLIC_APP_URL`** and **`PUBLIC_API_URL`** with **`https://`** and set **`COOKIE_SECURE=true`** so auth cookies are marked secure.

## Production (Ubuntu VM)

Step-by-step host setup (PostgreSQL 18, nginx, UFW, systemd unit for the API, graceful reloads, dev on the same machine): **`docs/UBUNTU_SERVER_SETUP.md`**.

Targets a **local or LAN** machine (no public domain): users open something like **`http://192.168.x.x`** or **`http://hostname.local`**. Set **`PUBLIC_APP_URL`** and **`CORS_ORIGINS`** to that exact origin; use **`COOKIE_SECURE=false`** with plain HTTP. Deployed checkout: **`/opt/promptDeck`** (see `deploy/` samples).

## Deploy artifacts (samples)

- **API process:** `deploy/systemd/promptdeck-api.service` — expects repo at `/opt/promptDeck`; adjust `User`, `WorkingDirectory`, and `EnvironmentFile` (e.g. `/etc/promptdeck/.env` with `DATABASE_URL`, `JWT_SECRET_KEY`, `STORAGE_ROOT`, `PUBLIC_APP_URL`, `CORS_ORIGINS`).
- **Reverse proxy:** `deploy/nginx/promptdeck.conf.sample` — port **80** redirects to **HTTPS** on **443** (self-signed or real certs); static files and `/api/` + `/a/` proxies on 443 only; sample includes baseline security headers (see comments in file for HSTS/CSP notes). Plain HTTP-only nginx: see **`docs/UBUNTU_SERVER_SETUP.md` §3.2**. LAN **IP** + self-signed: **§3.3** (cert SAN + `PUBLIC_APP_URL` / `CORS_ORIGINS` / `COOKIE_SECURE`).
- **Backups:** `scripts/backup_pg.sh` — gzip `pg_dump` using `DATABASE_URL` (async URL is rewritten to `postgresql://` for libpq).

After deploy: `alembic upgrade head` (same as `just db-migrate` from `backend/`; on a **fresh** DB this one pass creates the full schema). Run `scripts/bootstrap_users.py` once if you need initial login accounts (not the editor unless `ENVIRONMENT=development` or `BOOTSTRAP_DEMO_USERS=1`). Use `scripts/seed.py` only for application data seeding (currently a no-op). Reload nginx, `systemctl restart promptdeck-api`.

**Note:** Initial users used to be created via `SEED_ADMIN_*` and `scripts/seed.py`. That is replaced by `BOOTSTRAP_ADMIN_*` / `BOOTSTRAP_EDITOR_*` and `scripts/bootstrap_users.py`. Update any saved `.env` keys accordingly.
