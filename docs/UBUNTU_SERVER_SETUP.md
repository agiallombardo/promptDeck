# Ubuntu server setup (promptDeck)

Step-by-step notes for a **single long-lived VM** running PostgreSQL, nginx, and promptDeck (FastAPI + static Vite build), aligned with `plans/humming-bouncing-toast.md` and `docs/RUNBOOK.md`.

**Scope:** Ubuntu **22.04 or 24.04 LTS**, `systemd`, **no Docker** for v1. Commands assume `sudo` where needed.

---

## 1. Baseline OS

### 1.1 Update and packages

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl ca-certificates git ufw unattended-upgrades
```

### 1.2 Time sync

Ubuntu ships **systemd-timesyncd** or **chrony**. Verify time is correct (JWT expiry, logs, backups):

```bash
timedatectl status
```

If not synchronized, enable NTP:

```bash
sudo timedatectl set-ntp true
```

### 1.3 Firewall (UFW)

Allow SSH first, then HTTP/HTTPS:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

**Dev-only:** if you must hit the API directly on `:8000`, restrict the source IP:

```bash
sudo ufw allow from YOUR_OFFICE_IP to any port 8000 proto tcp
```

Production should expose **only nginx** (80/443), not raw uvicorn.

### 1.4 Optional: dedicated app user

```bash
sudo adduser --disabled-password --gecos "" promptdeck
sudo mkdir -p /var/lib/promptdeck /var/www/promptdeck
sudo chown -R promptdeck:promptdeck /var/lib/promptdeck /var/www/promptdeck
```

Deploy the app and run the API as this user (see §6).

### 1.5 Kernel / limits (optional)

For many concurrent connections to Postgres + nginx, you may raise file descriptors. Create `/etc/security/limits.d/99-promptdeck.conf`:

```
* soft nofile 65535
* hard nofile 65535
```

And ensure `DefaultLimitNOFILE=65535` in `/etc/systemd/system.conf` if needed, then `sudo systemctl daemon-reexec`.

---

## 2. PostgreSQL 16

### 2.1 Install (Ubuntu PGDG)

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16
```

### 2.2 Create database and role

```bash
sudo -u postgres psql -c "CREATE USER promptdeck WITH PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE promptdeck OWNER promptdeck;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE promptdeck TO promptdeck;"
```

**Connection URL for the app** (asyncpg):

```text
postgresql+asyncpg://promptdeck:REPLACE_WITH_STRONG_PASSWORD@127.0.0.1:5432/promptdeck
```

Set `DATABASE_URL` in the API environment (see §7).

### 2.3 Listen and access

Default: Postgres listens on `localhost` only — correct for a single host with local API.

Check:

```bash
sudo grep listen_addresses /etc/postgresql/16/main/postgresql.conf
```

For **peer auth** from `sudo -u postgres`, leave `pg_hba.conf` as shipped. The app connects over TCP as user `promptdeck` using password auth (`scram-sha-256`); ensure a line like:

```
host    promptdeck    promptdeck    127.0.0.1/32    scram-sha-256
```

in `/etc/postgresql/16/main/pg_hba.conf`, then reload Postgres (§2.4).

### 2.4 Graceful reload vs restart

| Goal | Command |
|------|---------|
| Apply `postgresql.conf` / `pg_hba.conf` changes without dropping connections | `sudo systemctl reload postgresql` |
| Full restart (rare; brief outage) | `sudo systemctl restart postgresql` |
| Status | `sudo systemctl status postgresql` |
| Logs | `sudo journalctl -u postgresql -f` |

**During development** on the same machine: after schema migrations, you usually **do not** need to restart Postgres — only restart the **API** process.

---

## 3. nginx

### 3.1 Install

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 3.2 Roles

- Serve the **built frontend** from `/var/www/promptdeck` (or similar).
- **Proxy** `/api` and `/a` to the FastAPI app (same origin as the SPA or a dedicated host — match `public_app_url` and CORS in `backend/app/config.py`).

Example server block sketch (TLS in §3.3):

```nginx
server {
    listen 80;
    server_name promptdeck.example.com;
    root /var/www/promptdeck;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /a/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site under `/etc/nginx/sites-available/` → `sites-enabled/`, then:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3.3 TLS (Let’s Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d promptdeck.example.com
```

Set `cookie_secure=true` and `cors_origins` / `public_app_url` to `https://…` in production.

### 3.4 Graceful nginx reload

| Goal | Command |
|------|---------|
| Apply config without dropping idle connections | `sudo systemctl reload nginx` |
| Test config | `sudo nginx -t` |

---

## 4. Application runtime (uv, Node, repo)

Install as **root** or as `promptdeck` user (recommended for the deploy tree).

### 4.1 uv (Python toolchains)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: sudo apt install -y pipx && pipx ensurepath
```

### 4.2 Node 20+ and pnpm

Use **NodeSource** or **nvm**; example with NodeSource 20.x:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
corepack enable
corepack prepare pnpm@9.15.4 --activate
```

### 4.3 Clone and build

```bash
sudo -u promptdeck -i
cd /var/lib/promptdeck
git clone https://github.com/your-org/promptDeck.git app
cd app
just setup
cd frontend && pnpm run build
sudo cp -r dist/* /var/www/promptdeck/
```

Backend: `cd backend && uv sync` and set environment (§7).

---

## 5. Storage and paths

promptDeck stores uploads under **`STORAGE_ROOT`** (default `./data/storage` — not ideal in production).

On the server:

```bash
sudo mkdir -p /var/lib/promptdeck/storage
sudo chown promptdeck:promptdeck /var/lib/promptdeck/storage
```

Set `STORAGE_ROOT=/var/lib/promptdeck/storage` for the API service.

---

## 6. systemd: API service

### 6.1 Unit file

Create `/etc/systemd/system/promptdeck-api.service`:

```ini
[Unit]
Description=promptDeck FastAPI (uvicorn)
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=promptdeck
Group=promptdeck
WorkingDirectory=/var/lib/promptdeck/app/backend
EnvironmentFile=/var/lib/promptdeck/app/backend/.env
ExecStart=/home/promptdeck/.local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=3
# Graceful stop: let uvicorn finish in-flight requests
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Adjust `ExecStart` to the real path of `uv` (`which uv` as `promptdeck`).

**Development-style reload** on a server is usually **`systemctl restart promptdeck-api`** after deploy; for zero-downtime you would add multiple workers behind a process manager — v1 often accepts a short restart window.

### 6.2 Commands

```bash
sudo systemctl daemon-reload
sudo systemctl enable promptdeck-api
sudo systemctl start promptdeck-api
sudo systemctl status promptdeck-api
sudo journalctl -u promptdeck-api -f
```

### 6.3 Graceful restart patterns

| Service | Graceful | Hard restart |
|---------|----------|--------------|
| **nginx** | `sudo systemctl reload nginx` | `sudo systemctl restart nginx` |
| **PostgreSQL** | `sudo systemctl reload postgresql` | `sudo systemctl restart postgresql` |
| **promptdeck-api** | `sudo systemctl restart promptdeck-api` (brief downtime) | same |

After editing any **`.service` file**: `sudo systemctl daemon-reload` then `sudo systemctl restart promptdeck-api`.

---

## 7. Environment variables (production)

Place in `/var/lib/promptdeck/app/backend/.env` (mode `600`, owner `promptdeck`):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://…@127.0.0.1:5432/promptdeck` |
| `JWT_SECRET_KEY` | ≥ 32 random bytes |
| `STORAGE_ROOT` | `/var/lib/promptdeck/storage` |
| `PUBLIC_APP_URL` | `https://promptdeck.example.com` (no trailing slash) |
| `CORS_ORIGINS` | JSON array in `.env`, e.g. `["https://promptdeck.example.com"]` (matches `backend/app/config.py`) |
| `COOKIE_SECURE` | `true` behind HTTPS |
| `ENVIRONMENT` | `production` |

Run migrations:

```bash
cd /var/lib/promptdeck/app/backend
sudo -u promptdeck env $(cat .env | xargs) uv run alembic upgrade head
```

(Or use `--env-file` / a small wrapper script.)

---

## 8. Dev on the same Ubuntu box

You can run **Postgres + nginx + systemd API** “like production” and still use **`just dev`** for rapid UI work:

1. Keep PostgreSQL and nginx as above.
2. Stop the packaged API while developing: `sudo systemctl stop promptdeck-api`.
3. From the repo: `just dev` (API `:8000`, Vite `:5173`). Point browser at Vite; it proxies `/api` and `/a` per `frontend/vite.config.ts`.

Or run only Vite against the **systemd** API:

```bash
cd frontend && pnpm dev
```

**Do not** run two processes on port 8000.

**Reload Postgres** only when you change `pg_hba` / major settings — not for normal app deploys.

---

## 9. Optional quality-of-life

- **`unattended-upgrades`** for security patches (reboot if kernel updates require it).
- **Log rotation:** nginx logs are usually handled by `logrotate`; app logs go to **journald** (`journalctl -u promptdeck-api`).
- **Backups:** `pg_dump` for DB + tar `/var/lib/promptdeck/storage` on a schedule.

---

## 10. Quick checklist

- [ ] UFW: SSH + 80/443 (and optional restricted dev ports).
- [ ] PostgreSQL 16: DB + user + `DATABASE_URL`.
- [ ] `alembic upgrade head` + `scripts/seed.py` if needed.
- [ ] `STORAGE_ROOT` on disk with correct ownership.
- [ ] Frontend build copied to nginx `root`.
- [ ] nginx proxies `/api` and `/a` to `127.0.0.1:8000`.
- [ ] TLS + `cookie_secure` + CORS + `public_app_url`.
- [ ] `promptdeck-api.service` enabled and healthy.
- [ ] `just verify` passes in CI before/after deploy.

For application behavior and verification commands, see **`docs/RUNBOOK.md`** and **`CLAUDE.md`**.
