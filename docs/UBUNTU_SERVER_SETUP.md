# Ubuntu server setup (promptDeck)

Step-by-step notes for a **single long-lived VM** running PostgreSQL, nginx, and promptDeck (FastAPI + static Vite build), aligned with `docs/RUNBOOK.md`.

**App checkout:** clone or sync the repo to **`/opt/promptDeck`** (repo root: `backend/`, `frontend/`, etc.).

**Hosting:** **local / LAN** — no public DNS name. Users reach the app at something like **`http://192.168.x.x`** or **`http://server-name.local`**. Set `PUBLIC_APP_URL` and `CORS_ORIGINS` to that **exact** origin (scheme + host + port if not 80). Plain HTTP is expected; keep **`COOKIE_SECURE=false`** unless you add TLS yourself.

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

Allow SSH first, then HTTP (HTTPS is optional unless you add TLS):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
# Optional — only if you enable HTTPS in nginx:
# sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

**Dev-only:** if you must hit the API directly on `:8005`, restrict the source IP:

```bash
sudo ufw allow from YOUR_OFFICE_IP to any port 8005 proto tcp
```

Expose **only nginx** on the LAN (port **80** for typical HTTP), not raw uvicorn, unless you are debugging.

### 1.4 Optional: dedicated app user

```bash
sudo adduser --disabled-password --gecos "" promptdeck
sudo mkdir -p /opt/promptDeck /var/lib/promptdeck
sudo chown -R promptdeck:promptdeck /opt/promptDeck /var/lib/promptdeck
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

## 2. PostgreSQL 18

### 2.1 Install (Ubuntu PGDG)

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo apt update
sudo apt install -y postgresql-18 postgresql-client-18
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
sudo grep listen_addresses /etc/postgresql/18/main/postgresql.conf
```

For **peer auth** from `sudo -u postgres`, leave `pg_hba.conf` as shipped. The app connects over TCP as user `promptdeck` using password auth (`scram-sha-256`); ensure a line like:

```
host    promptdeck    promptdeck    127.0.0.1/32    scram-sha-256
```

in `/etc/postgresql/18/main/pg_hba.conf`, then reload Postgres (§2.4).

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

- Serve the **built frontend** from **`/opt/promptDeck/frontend/dist`** (Vite `pnpm run build` output).
- **Proxy** `/api` and `/a` to the FastAPI app (same origin as the SPA or a dedicated host — match `public_app_url` and CORS in `backend/app/config.py`).

Example **plain HTTP** server block (typical for local hosting). Prefer copying **`deploy/nginx/promptdeck.conf.sample`** and editing paths if needed.

```nginx
server {
    listen 80;
    server_name _;
    root /opt/promptDeck/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /a/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

Enable the site under `/etc/nginx/sites-available/` → `sites-enabled/`, then:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3.3 Optional: HTTPS (self-signed, LAN IP)

For **local-only** use you can skip this section and stay on **HTTP**.

To serve the UI on **port 443** with a **self-signed** certificate when users open the app by **IP** (no hostname):

1. **Pick the IP** clients will type (e.g. `192.168.1.50`). The certificate must list that IP in **Subject Alternative Name** or browsers will reject the connection even after “Advanced”.

2. **Generate cert + key** (OpenSSL 1.1.1+; Ubuntu 22.04/24.04 are fine):

```bash
sudo mkdir -p /etc/ssl/promptdeck
sudo openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /etc/ssl/promptdeck/privkey.pem \
  -out /etc/ssl/promptdeck/fullchain.pem \
  -subj "/CN=192.168.1.50" \
  -addext "subjectAltName=IP:192.168.1.50"
```

Replace **`192.168.1.50`** twice with your server’s LAN IP. For multiple IPs, extend SAN, e.g. `subjectAltName=IP:192.168.1.50,IP:10.0.0.5`.

```bash
sudo chmod 640 /etc/ssl/promptdeck/privkey.pem
sudo chgrp root /etc/ssl/promptdeck/privkey.pem
```

3. **nginx:** enable the **`listen 443 ssl`** `server` block from **`deploy/nginx/promptdeck.conf.sample`** (paths already point at `/etc/ssl/promptdeck/`). Optionally replace the port **80** `server` with a single line `return 301 https://$host$request_uri;` so only HTTPS is used.

4. **Firewall:** `sudo ufw allow 443/tcp` (and reload UFW if you use it).

5. **API env (§7):** use the **same origin** the browser uses (HTTPS, IP, **no** `:443` in the URL):

| Variable | Example |
|----------|---------|
| `PUBLIC_APP_URL` | `https://192.168.1.50` |
| `CORS_ORIGINS` | `["https://192.168.1.50"]` |
| `COOKIE_SECURE` | `true` |

Restart **`promptdeck-api`** after changing env. Run **`sudo nginx -t`** then **`sudo systemctl reload nginx`**.

Browsers will show a **warning** for self-signed certs; that is expected until you install a trust anchor or use a real hostname with a CA (e.g. Let’s Encrypt — not applicable to arbitrary public IPs in the usual ACME flow).

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

### 4.2 Node.js Active LTS and pnpm

Install the **current Active LTS** from [Node.js releases](https://nodejs.org/en/about/releases) (24.x **Krypton** as of early 2026). Example with **NodeSource** 24.x:

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
corepack enable
corepack prepare pnpm@10.33.0 --activate
```

Pin matches `frontend/package.json` (`packageManager`). To pick up newer **pnpm 10.x** releases without editing the file, use `corepack prepare pnpm@latest-10 --activate` after checking compatibility.

Alternatively use **nvm**: `nvm install --lts` (tracks Active LTS).

### 4.3 Clone and build

```bash
sudo -u promptdeck git clone https://github.com/your-org/promptDeck.git /opt/promptDeck
cd /opt/promptDeck
just setup
cd frontend && pnpm run build
```

nginx should use `root /opt/promptDeck/frontend/dist;` (see §3.2 and `deploy/nginx/promptdeck.conf.sample`). Backend: `cd /opt/promptDeck/backend && uv sync` and set environment (§7).

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
After=network.target postgresql.service
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=promptdeck
Group=promptdeck
WorkingDirectory=/opt/promptDeck/backend
EnvironmentFile=/etc/promptdeck/.env
ExecStart=/opt/promptDeck/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8005 --proxy-headers
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Match `deploy/systemd/promptdeck-api.service` in the repo. After `uv sync` in `backend/`, `.venv/bin/uvicorn` exists; adjust `ExecStart` only if you use a different layout.

**Development-style reload** on a server is usually **`systemctl restart promptdeck-api`** after deploy; for zero-downtime you would add multiple workers behind a process manager — v1 often accepts a short restart window.

### 6.2 Commands

Create **`/etc/promptdeck/.env`** (§7) **before** the first start. If the unit is already in a restart loop with `Failed to load environment files`, run **`sudo systemctl stop promptdeck-api`**, add the file, then `daemon-reload` and `start` again.

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

Create **`/etc/promptdeck/.env`** (same file as `EnvironmentFile` in the unit). Restrict permissions (e.g. `chmod 640`, `chgrp promptdeck` so the service user can read it):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://…@127.0.0.1:5432/promptdeck` |
| `JWT_SECRET_KEY` | ≥ 32 random bytes |
| `STORAGE_ROOT` | `/var/lib/promptdeck/storage` |
| `PUBLIC_APP_URL` | Same origin browsers use, e.g. `http://192.168.1.50` or `https://192.168.1.50` (no trailing slash; omit `:443`) |
| `CORS_ORIGINS` | JSON array matching that origin, e.g. `["http://192.168.1.50"]` or `["https://192.168.1.50"]` (see `backend/app/config.py`) |
| `COOKIE_SECURE` | `false` for plain HTTP on the LAN; `true` when nginx serves **HTTPS** (§3.3) |
| `ENVIRONMENT` | `production` |

Run migrations (one command for both **first install** on an empty database and **upgrades** when new revisions exist):

```bash
cd /opt/promptDeck/backend
sudo -u promptdeck bash -c 'set -a && . /etc/promptdeck/.env && set +a && uv run alembic upgrade head'
```

On a fresh database, `upgrade head` applies every revision in order—no extra steps per table. When you deploy new app code that adds `alembic/versions/*.py`, run the same command again.

(Or use a small wrapper that loads the same env as systemd.)

---

## 8. Dev on the same Ubuntu box

You can run **Postgres + nginx + systemd API** “like production” and still use **`just dev`** for rapid UI work:

1. Keep PostgreSQL and nginx as above.
2. Stop the packaged API while developing: `sudo systemctl stop promptdeck-api`.
3. From the repo: `cd /opt/promptDeck` then `just dev` (API `:8005`, Vite `:5174` by default). Point browser at Vite; it proxies `/api` and `/a` per `frontend/vite.config.ts`. Override with `VITE_DEV_PORT` if needed.

Or run only Vite against the **systemd** API:

```bash
cd /opt/promptDeck/frontend && pnpm dev
```

**Do not** bind the API twice on port 8005 (e.g. systemd uvicorn and a duplicate manual `uvicorn`).

**Reload Postgres** only when you change `pg_hba` / major settings — not for normal app deploys.

---

## 9. Optional quality-of-life

- **`unattended-upgrades`** for security patches (reboot if kernel updates require it).
- **Log rotation:** nginx logs are usually handled by `logrotate`; app logs go to **journald** (`journalctl -u promptdeck-api`).
- **Backups:** `pg_dump` for DB + tar `/var/lib/promptdeck/storage` on a schedule.

---

## 10. Quick checklist

- [ ] UFW: SSH + **80** (add **443** only if you use HTTPS).
- [ ] PostgreSQL 18: DB + user + `DATABASE_URL`.
- [ ] `alembic upgrade head` + `scripts/seed.py` if needed.
- [ ] `STORAGE_ROOT` on disk with correct ownership.
- [ ] Frontend built to `/opt/promptDeck/frontend/dist` and nginx `root` matches.
- [ ] nginx proxies `/api` and `/a` to `127.0.0.1:8005`.
- [ ] `PUBLIC_APP_URL` + `CORS_ORIGINS` match how users open the app; `COOKIE_SECURE` matches HTTP vs HTTPS.
- [ ] `promptdeck-api.service` enabled and healthy.
- [ ] `just verify` passes in CI before/after deploy.

For application behavior and verification commands, see **`docs/RUNBOOK.md`** and **`CLAUDE.md`**.
