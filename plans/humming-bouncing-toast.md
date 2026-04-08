# promptDeck / Recessed Studio — Implementation Plan (v2)

## Context

The repo at `/Users/agiallombardo/Repo/powerpointReplaced` currently holds only design artifacts:
- `DESIGN.md` — "Synthetic Architecture / Tactical Obsidian" dark design system.
- `recessed_studio_prd.html` — full PRD for promptDeck.
- `stitch_floating_dark_modules_prd/*/code.html` — static mockups for 5 key screens.

**Why build this:** AI-generated HTML "website slides" have replaced traditional PowerPoint decks inside the organization. Today there is no good way to share an in-progress deck with colleagues, collect coordinate-pinned feedback, view history, or "compile" the final deck for external distribution (zipping 100 files into email is not acceptable). This app solves that for internal corporate use.

**Intended outcome v1:** An internal, single-tenant web app where a user can upload a `.html` or `.zip` deck, preview it in a distraction-free canvas, navigate slides, leave coordinate-pinned comments, share a scoped link with a colleague, and export the deck to a single PDF or a single self-contained HTML file. An Admin page provides rich logging/troubleshooting visibility. The codebase is explicitly built so that a coding LLM ("vibe coding") can reliably navigate, test, and extend it.

## v1 Scope — locked via Q&A

**In scope**
- Upload (single `.html` OR `.zip` bundle)
- Display (iframe canvas, prev/next, version selector)
- Review / comment (coordinate-pinned, threaded; **manual refresh**, not real-time)
- Share (scoped link with role + optional expiry)
- Export (PDF via Playwright, single-file HTML via inliner)
- Local email/password auth
- Admin page with enhanced logging / troubleshooting
- LLM-friendly test + verification harness (backend + frontend)
- CLAUDE.md, `.cursorrules`, and a conventions doc driving LLM-assisted development

**Explicitly roadmap / not in v1**
- Real-time updates (SSE / WebSockets / live comments)
- AI regeneration ("Force Refresh" via LiteLLM → Claude or GPT)
- Entra ID / Azure AD OIDC SSO
- Azure Blob storage driver (interface ready; local FS implementation only for v1)
- Multi-tenant / organizations (single tenant only)
- GitLab / GitHub repo sync for presentation versions
- Docker / docker-compose (runs directly on a full instance, managed by systemd)
- Mobile: generation + export are **explicitly never supported on mobile**; mobile is view + comment + share only

## Technology Decisions

| Area | Decision |
|---|---|
| Backend | Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 async + asyncpg + Alembic |
| DB | PostgreSQL 16 (single local install on the host) |
| Frontend | React 18 + Vite 5 + TypeScript 5 + **Tailwind CSS 4** (CSS-first `@theme` config) |
| State | TanStack Query v5 (server state) + Zustand 4 (UI state) |
| Jobs (v1) | FastAPI `BackgroundTasks` + DB `export_jobs` table, frontend polls status |
| Storage | Abstraction with drivers: `LocalFSStorage` (v1), `AzureBlobStorage` (roadmap stub) |
| Auth | Local email+password (argon2), JWT access + HttpOnly refresh cookie; Entra ID OIDC = roadmap |
| PDF export | Playwright (Python) + `pypdf` merge |
| Single-HTML export | Custom Python inliner (`selectolax`) — no Node dependency |
| Slide identification | Iframe sandbox + injected `probe.js`: auto-detect `[data-slide]` → top-level `<section>` → single-slide fallback; `postMessage` protocol |
| Logging | `structlog` JSON logs → stdout (systemd journal) + DB ring buffer (`app_logs` table, capped) surfaced in Admin UI |
| Process mgmt | systemd units: `promptdeck-api.service`, `promptdeck-web.service` (nginx serves built frontend); Postgres is a system service |
| Runtime | Python deps via `uv`, Node deps via `pnpm`, no containers |

## Hosting Model

Single long-lived VM (v1). Future migration target: Azure App Service / Container App with Entra ID app registration + Azure Blob Storage for object storage. Code is structured so that the move consists of swapping the storage driver, enabling the OIDC router, and building container images — no architectural rework.

## Architecture

```
                   Browser
                     │
                HTTPS (nginx)
                     │
       ┌─────────────┴──────────────┐
       │                            │
  static /assets              FastAPI (uvicorn)
  built frontend                    │
  (/var/www/promptdeck)             │
                              ┌─────┴─────┐
                              │           │
                        PostgreSQL    Local FS
                        (pg_dump      /var/lib/promptdeck/
                         backups)     storage/
                                      ├── presentations/
                                      │   └── {pres_id}/v{n}/...
                                      └── exports/
                                          └── {job_id}.pdf

   In-process:
     FastAPI BackgroundTasks for:
       - zip extraction + manifest parsing (upload)
       - PDF render via Playwright
       - Single-HTML inliner
     structlog → stdout + DB (app_logs ring buffer)
```

No Redis, no separate worker process, no docker. Everything is a couple of systemd units.

## Repository Layout

```
powerpointReplaced/
├── README.md
├── CLAUDE.md                     # authoritative LLM runbook (see §"LLM Vibe Coding")
├── .cursorrules                  # cursor IDE rules mirror of CLAUDE.md highlights
├── DESIGN.md                     # existing
├── recessed_studio_prd.html      # existing
├── stitch_floating_dark_modules_prd/   # existing mockups, reference
├── pyproject.toml                # workspace tooling (ruff/pyright at root)
├── justfile                      # single-entry commands for humans + LLMs
├── scripts/
│   ├── verify.sh                 # run all checks; exit 0 or diagnostic output
│   ├── dev.sh                    # start api + vite in parallel
│   ├── seed.py                   # seed admin user + sample presentation
│   └── e2e_smoke.py              # end-to-end golden path script
├── docs/
│   ├── CONVENTIONS.md            # naming, layering, error handling, testing
│   ├── RUNBOOK.md                # install, deploy, troubleshoot
│   ├── PROBE_PROTOCOL.md         # iframe ↔ host message contract
│   ├── API.md                    # generated from OpenAPI
│   ├── ROADMAP.md                # deferred items with rationale
│   ├── SECURITY.md
│   └── adr/
│       ├── 0001-stack-choices.md
│       ├── 0002-no-realtime-v1.md
│       └── 0003-iframe-sandbox-model.md
│
├── backend/
│   ├── pyproject.toml            # uv managed; py3.12
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py               # FastAPI factory + middleware + logging setup
│   │   ├── config.py             # pydantic-settings
│   │   ├── deps.py               # db, current_user, require_role, acl
│   │   ├── logging_conf.py       # structlog config + DB handler
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/           # user, presentation, version, slide,
│   │   │                         # thread, comment, share, export_job,
│   │   │                         # app_log, audit_log
│   │   ├── schemas/              # pydantic v2 DTOs
│   │   ├── routers/
│   │   │   ├── auth.py           # login, logout, refresh, me
│   │   │   ├── presentations.py
│   │   │   ├── versions.py
│   │   │   ├── assets.py         # serves uploaded HTML/CSS/JS (cookieless host)
│   │   │   ├── comments.py
│   │   │   ├── shares.py
│   │   │   ├── exports.py
│   │   │   └── admin.py          # logs, jobs, users, stats (admin-only)
│   │   ├── services/
│   │   │   ├── upload.py         # zip-slip safe, size caps, manifest extraction
│   │   │   ├── slide_manifest.py # HTML parse via selectolax
│   │   │   ├── pdf_export.py     # Playwright
│   │   │   ├── html_inliner.py
│   │   │   ├── shares.py         # token gen + hash
│   │   │   ├── acl.py            # role resolution across user + share JWT
│   │   │   └── admin_logs.py     # query the ring buffer
│   │   ├── jobs/
│   │   │   ├── background.py     # typed wrapper around BackgroundTasks
│   │   │   ├── export_runner.py
│   │   │   └── upload_runner.py
│   │   ├── storage/
│   │   │   ├── base.py           # Storage protocol
│   │   │   ├── local.py          # v1 driver
│   │   │   └── azure_blob.py     # roadmap stub with NotImplementedError
│   │   ├── security/
│   │   │   ├── jwt.py
│   │   │   ├── passwords.py      # argon2
│   │   │   ├── csp.py            # strict CSP for asset route
│   │   │   └── ratelimit.py      # slowapi
│   │   ├── probe/probe.js        # served to iframe by assets router
│   │   └── tests/
│   │       ├── conftest.py       # pg testcontainer OR psql template db
│   │       ├── factories.py      # polyfactory
│   │       ├── test_upload.py
│   │       ├── test_comments.py
│   │       ├── test_shares.py
│   │       ├── test_exports.py
│   │       ├── test_admin.py
│   │       └── fixtures/
│   │           ├── sample_deck.html
│   │           └── sample_bundle.zip
│   └── scripts/
│       ├── run_api.sh            # systemd ExecStart
│       └── make_admin.py
│
├── frontend/
│   ├── package.json              # vite 5, react 18.3, ts 5.5, tailwind 4
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── router.tsx
│       ├── styles/
│       │   ├── tailwind.css      # @import "tailwindcss"; @theme { ... } — v4 config
│       │   └── globals.css
│       ├── lib/
│       │   ├── api/              # openapi-typescript generated + typed fetch wrapper
│       │   ├── auth.ts
│       │   └── queryClient.ts
│       ├── stores/               # Zustand
│       ├── components/
│       │   ├── primitives/       # Button, Input, Modal, Drawer (vaul on mobile)
│       │   ├── layout/           # TopNav, ActionBar
│       │   ├── canvas/           # PresentationCanvas, SlideFrame, CommentMarker,
│       │   │                     # LoadingWireframe, ErrorPanel
│       │   ├── feedback/         # FeedbackSidebar, CommentThread, CommentComposer
│       │   ├── version/          # VersionSelector (simple dropdown v1,
│       │   │                     # full drawer UI = roadmap)
│       │   ├── share/            # ShareModal
│       │   ├── export/           # ExportModal (desktop only)
│       │   └── admin/            # AdminDashboard, LogsTable, JobsTable, UserList
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── FileManagerPage.tsx
│       │   ├── PresentationPage.tsx
│       │   ├── ShareEntryPage.tsx
│       │   └── AdminPage.tsx
│       ├── hooks/
│       │   ├── usePresentation.ts
│       │   ├── useComments.ts    # refetch on window focus + manual Refresh btn
│       │   └── useAdminLogs.ts
│       └── tests/
│           ├── setup.ts
│           ├── components/...    # vitest + React Testing Library
│           └── e2e/...           # Playwright
│
├── deploy/
│   ├── systemd/
│   │   ├── promptdeck-api.service
│   │   └── promptdeck-web.service   # (or nginx-served static, see docs/RUNBOOK.md)
│   ├── nginx/
│   │   └── promptdeck.conf          # serves frontend + proxies /api and /a
│   └── postgres/
│       └── init.sql
│
└── .github/ (or .gitlab-ci.yml)
    └── workflows/
        ├── verify.yml               # runs scripts/verify.sh
        └── release.yml
```

## Database Schema (PostgreSQL 16)

UUID PKs, `timestamptz` everywhere, soft delete via `deleted_at` on user-facing entities.

- **users** — `id, email citext uniq, display_name, avatar_url, password_hash, role ∈ {admin,editor,commenter,viewer}, last_login_at, created_at, deleted_at`
- **presentations** — `id, owner_id, title, description, current_version_id, created_at, updated_at, deleted_at`; idx `(updated_at desc)`
- **presentation_versions** — `id, presentation_id, version_number, origin ∈ {upload,manual_edit}, created_by, storage_kind ∈ {single_html,bundle}, storage_prefix, entry_path, sha256, size_bytes, created_at`; uniq `(presentation_id, version_number)`. `origin='ai_regen'` added in roadmap.
- **slides** — `id, version_id, index, selector, title, thumbnail_path`; uniq `(version_id, index)`
- **comment_threads** — `id, presentation_id, version_id, slide_index, anchor_x real, anchor_y real, status ∈ {open,resolved}, created_by, created_at, resolved_at`; idx `(presentation_id, slide_index)`
- **comments** — `id, thread_id, author_id, body, body_format default 'markdown', created_at, edited_at, deleted_at`
- **share_links** — `id, presentation_id, token_hash bytea, role ∈ {viewer,commenter,editor}, expires_at, created_by, revoked_at`; partial uniq idx on `token_hash where revoked_at is null`
- **export_jobs** — `id, presentation_id, version_id, format ∈ {pdf,single_html}, scope jsonb, options jsonb, status ∈ {queued,running,succeeded,failed}, output_path, error, progress int (0..100), created_by, created_at, started_at, finished_at`
- **app_logs** (ring buffer, admin page) — `id bigserial, ts, level, event, logger, request_id, user_id, path, status_code, latency_ms, payload jsonb`; idx `(ts desc)`, `(level, ts desc)`, `(request_id)`. Capped by periodic `DELETE` (e.g., keep last 1M rows or last 30 days, whichever is smaller). Also written to stdout for systemd journal.
- **audit_log** — `id bigserial, actor_id, action, target_kind, target_id, metadata jsonb, ip inet, created_at`; indexed by `(created_at desc)`.

Roadmap tables (kept in design docs, not migrations): `organizations`, `memberships`, `ai_generation_jobs`.

## Key API Endpoints (`/api/v1`)

**Auth** — `POST /auth/login` (email+password), `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`.

**Presentations** — `GET|POST /presentations`, `GET|PATCH|DELETE /presentations/{id}`.

**Versions** — `POST /presentations/{id}/versions` (multipart), `GET /presentations/{id}/versions`, `POST /presentations/{id}/versions/{vid}/activate`.

**Assets** (cookieless host or cross-subdomain) — `GET /a/{version_id}/*path`: signed HMAC query param, 1h TTL, strict CSP, injects `probe.js` into entry HTML.

**Comments** — `GET|POST /presentations/{id}/threads`, `POST /threads/{tid}/comments`, `PATCH /threads/{tid}`, `DELETE /comments/{cid}`. **No SSE in v1** — client fetches on mount, on window focus, and via a manual Refresh control.

**Shares** — `POST|GET /presentations/{id}/shares`, `DELETE /shares/{sid}`, `POST /shares/exchange`.

**Exports** — `POST /presentations/{id}/exports`, `GET /exports/{job_id}` (polled by client every 1–2s until terminal).

**Admin** (role=admin) — `GET /admin/logs?level=&since=&request_id=&user_id=&limit=`, `GET /admin/jobs`, `GET /admin/users`, `GET /admin/stats`, `GET /admin/audit`, `POST /admin/logs/search` (full-text over `payload`).

Every HTTP request gets a `X-Request-ID` (generated if absent) which is set as a structlog contextvar and written to `app_logs`. The frontend surfaces the request ID in toast-errors so users can paste it into bug reports that admins can look up immediately.

## Frontend Architecture

**Tailwind 4** (CSS-first). `src/styles/tailwind.css`:
```css
@import "tailwindcss";

@theme {
  --color-primary: #00E5FF;
  --color-bg-void: #050507;
  --color-bg-recessed: #0A0B0E;
  --color-bg-elevated: #16181D;
  --color-border: #1E2128;
  --color-text-main: #E2E4E9;
  --color-text-muted: #828796;
  --color-accent-warning: #FF2A55;

  --font-heading: "Space Grotesk", sans-serif;
  --font-ui: "JetBrains Mono", monospace;
  --font-body: "Geist", sans-serif;

  --shadow-recessed: inset 0 0 20px rgba(0,0,0,0.8);
  --shadow-elevated: 0 0 0 1px #2A2D35, 0 20px 40px rgba(0,0,0,0.9);

  --radius-*: initial;
  --radius-sharp: 4px;
}
```
No `tailwind.config.ts`. `<html class="dark">` permanently; no light mode.

**State:** TanStack Query for server state. Zustand for UI state only (`commentMode`, `activeSlideIndex`, drawer visibility, connection health indicator — reused later for real-time). Because v1 is not real-time, caches are invalidated by: (a) route change, (b) window focus, (c) explicit Refresh button in the top nav, (d) after a successful mutation.

**Routes:** `/login`, `/files`, `/p/:id`, `/share/:token`, `/admin` (admin-only).

**Iframe + probe protocol:** `<iframe sandbox="allow-scripts" src="https://assets.{host}/a/{version_id}/index.html?slide=0&sig=...">`. The assets router injects a `<script src="/probe.js">` (served from the asset origin) into the entry HTML head at serve time. `probe.js` detects slides in order `[data-slide]` → top-level `<section>` → single-slide fallback, hides inactive slides, listens for `{type:'goto'|'setCommentMode'}` from parent, posts `{type:'manifest',count,titles}` on load and `{type:'slide-click',slide,x,y}` normalized on click in comment mode.

**Mobile:** responsive canvas, bottom-up drawers via `vaul`, long-press to enter comment mode, large touch markers. **Share button is available on mobile; Export and (future) Generate are hidden below `md` breakpoint.**

## Critical Flows

- **Upload:** `POST /presentations` → `POST /versions` multipart → service stores blob/extracts zip (zip-slip safe) → `slide_manifest.py` parses entry HTML → rows inserted → `current_version_id` updated → response returns manifest. Frontend navigates to `/p/{id}`.
- **View + comment:** iframe loads signed asset URL → probe posts manifest → user toggles comment mode → clicks slide → probe posts coords → sidebar opens composer → `POST /threads` → frontend invalidates thread query.
- **Share-link access:** `/share/:token` → `POST /shares/exchange` → viewer JWT held in memory → navigate to `/p/{id}`.
- **PDF export (desktop only):** `POST /exports {format:'pdf', scope}` → row created status=queued → returned immediately → FastAPI `BackgroundTask` runs Playwright per slide using `?slide=N&print=1`, renders `page.pdf({printBackground:true, width:'1280px', height:'720px'})`, merges via `pypdf`, optional annotation overlay → row updated status=succeeded + `output_path` → `GET /exports/{id}` returns signed download URL.
- **Single-HTML export:** same job table, `html_inliner.py` walks entry HTML with selectolax and inlines CSS/JS/images as data URIs → single `.html` blob.

## Admin Page & Enhanced Logging

**Goal:** enable a non-developer admin (or a coding LLM during development) to figure out "what happened" without SSHing into the box.

**Log sources** all funneled through `structlog`:
1. HTTP access middleware — method, path, status, latency, request ID, user ID, IP.
2. Business events — `presentation.uploaded`, `comment.created`, `share.exchanged`, `export.completed`, etc., with structured payloads.
3. Errors — exception class, traceback (truncated), request ID.
4. Job lifecycle — `export.started`, `export.progress`, `export.finished|failed` with job ID.

Each log record is dual-written: stdout JSON (for systemd journal / future log aggregators) and a row in `app_logs` (capped ring buffer).

**Admin UI surfaces:**
- **Logs tab** — live-ish table (refreshed on demand + auto every 10s), filter by level/user/request ID/path/date range, click a row to expand the full `payload` JSON, "Copy request ID" button. Keyboard shortcut `/` focuses filter.
- **Jobs tab** — list of `export_jobs` with status, progress, error, re-run button for `failed`.
- **Presentations tab** — recent uploads with file size, storage path, slide count, link to view.
- **Users tab** — list, last login, role, reset-password link (emails deferred; shows token inline for v1).
- **Audit tab** — security-relevant events from `audit_log`.
- **Stats tab** — counts, recent activity sparkline, storage usage.

The Admin page is the primary "debugger" for v1. Any bug report from a user should be resolvable by searching `app_logs` by request ID.

## Security

- Iframe `sandbox="allow-scripts"` only; assets served from a distinct cookieless host or path prefix with CSP `default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline' 'self'; img-src 'self' data:; frame-ancestors 'self'`.
- Signed asset URLs (HMAC of `version_id|exp|user_id|role`, 1h TTL).
- Zip-slip guard: reject `..`, absolute, symlinks; caps per-file 10MB, total 50MB, count 1000, ratio 3×.
- Share tokens: 32 random bytes, stored as sha256 hash, plaintext shown once.
- Passwords: argon2id via `argon2-cffi`.
- Sessions: JWT access (15 min) + HttpOnly refresh cookie (14 d), rotation on refresh.
- Rate limits (slowapi): `/auth/*` 5/min/IP, uploads 20/hr/user, `/shares/exchange` 10/min/IP.
- ACL middleware resolves role from user JWT OR share JWT and applies per-presentation checks.
- Audit log writes on: login, login fail, share create/revoke/exchange, version create, export, role change, admin-page access.

## LLM Vibe Coding — Explicit Best Practices

This is first-class. The code must be built so an LLM (Claude Code, Cursor) can extend it reliably on its own.

**`CLAUDE.md` (repo root)** contains:
1. **Project elevator pitch** — 5 lines.
2. **Directory map** — annotated tree (key files, where to add things).
3. **Command cheat sheet** — every verified command in one place:
   ```
   just setup            # install deps (uv sync, pnpm install, playwright install)
   just dev              # run api + web concurrently
   just verify           # run ALL checks; exit 0 or print fix hints
   just test-backend     # pytest
   just test-frontend    # vitest + RTL
   just test-e2e         # playwright e2e
   just smoke            # scripts/e2e_smoke.py
   just lint             # ruff + eslint + prettier check
   just types            # pyright + tsc --noEmit
   just db-migrate       # alembic upgrade head
   just db-reset         # drop+recreate, apply migrations, seed
   just api-contract     # regenerate frontend/src/lib/api/ from /openapi.json
   ```
4. **"How to add X" recipes** — one section each, with exact files to touch:
   - Add a new API endpoint
   - Add a new DB field
   - Add a new frontend page
   - Add a new component
   - Add a new test
   - Add a new log event
   - Add a new admin log filter
5. **Non-negotiable rules** —
   - Always run `just verify` before declaring work done.
   - Never hand-edit `frontend/src/lib/api/*` — regenerate via `just api-contract`.
   - Every new endpoint needs: pydantic schemas, router function, test, OpenAPI re-gen.
   - Every new business event must emit a `structlog` event and be visible in Admin Logs.
   - Every new background job writes status + progress to its job table row.
   - Prefer editing an existing file over creating a new one.
6. **Debugging flow** — "find the request ID in the UI toast → open `/admin/logs` → filter by request ID → inspect payload → fix → add a regression test."
7. **Scope boundaries** — link to `docs/ROADMAP.md`; list what NOT to build.
8. **File size budget** — soft cap 400 LOC per file to keep LLM context-friendly.

**`.cursorrules`** — a compact (≤120 line) mirror of CLAUDE.md's rules section for Cursor users.

**`docs/CONVENTIONS.md`** — naming, typing discipline (no `any`, no untyped dicts at boundaries), error handling (domain exceptions → problem+json), pydantic schema split (Create/Read/Update), FastAPI router layering (router → service → repo/db), tests mirror source tree 1:1.

**`docs/adr/`** — one ADR per material decision (stack, no-realtime-v1, iframe model, logging design, LLM-first layout).

**OpenAPI-driven frontend client** — `openapi-typescript` generates `frontend/src/lib/api/types.ts` and `client.ts` from a committed `backend/openapi.json` snapshot. CI fails if the snapshot is stale. This gives the LLM a single source of truth and fails loudly on contract drift.

**Pre-commit (`lefthook` or `pre-commit`):** ruff format/check, pyright (changed files), eslint, prettier, tsc, vitest (related).

## Testing & Verification (LLM-friendly)

This is explicitly designed so an LLM can **write code → run one command → get deterministic, labeled pass/fail output → iterate**.

### Backend
- **pytest** + `pytest-asyncio` + `httpx.AsyncClient` against a real Postgres template DB.
- Fixtures via `polyfactory` for all models (`backend/app/tests/factories.py`).
- `conftest.py` provides `client`, `authed_client`, `admin_client`, `sample_deck_path`, `tmp_storage`.
- Each router has a paired test file (`test_<router>.py`) covering happy path + 3 error cases minimum.
- **Contract test:** `test_openapi_frozen.py` — loads `/openapi.json`, compares to committed snapshot; fails with a diff if drift. LLM fix: `just api-contract && git add`.
- **Log assertion helper:** `assert_logged(capsys, event="presentation.uploaded", level="info")` so tests can verify business events fire.
- **Smoke test `scripts/e2e_smoke.py`** — fully self-contained, reset DB → seed → upload fixture → create thread → create share link → exchange → export PDF → assert 3-page PDF. Prints `PASS` / `FAIL: <reason>`.

### Frontend
- **vitest** + `@testing-library/react` for unit/component tests.
- **msw** to mock the backend in component tests using the generated OpenAPI types (so tests break when contracts break).
- **Playwright** for e2e (`just test-e2e`) — runs against a locally started api + web; includes golden-path scenario matching the smoke script.
- **Storybook optional (roadmap).**
- **Visual sanity:** `@playwright/test` screenshot of `PresentationPage` vs a baseline (tolerance 0.1%) so design-token drift fails CI.

### Single-entry verification — `scripts/verify.sh`
```
#!/usr/bin/env bash
set -euo pipefail
section() { echo -e "\n===== $1 ====="; }

section "backend lint"          ; (cd backend && uv run ruff check . && uv run ruff format --check .)
section "backend types"         ; (cd backend && uv run pyright)
section "backend tests"         ; (cd backend && uv run pytest -q)
section "frontend lint"         ; (cd frontend && pnpm lint)
section "frontend types"        ; (cd frontend && pnpm tsc --noEmit)
section "frontend unit tests"   ; (cd frontend && pnpm test --run)
section "openapi contract"      ; (cd backend && uv run python -m app.scripts.check_openapi_snapshot)
section "smoke test"            ; (cd backend && uv run python ../scripts/e2e_smoke.py)
echo -e "\n✅ verify passed"
```
LLM workflow: after any change, `just verify`. First failure section = next thing to fix.

## Milestones

| # | Name | Deliverable |
|---|---|---|
| M0 | Repo + LLM scaffolding | `CLAUDE.md`, `.cursorrules`, `docs/`, `justfile`, `scripts/verify.sh` stub, empty backend/frontend projects that boot, one dummy test, CI green. |
| M1 | Auth + DB + logging | Users table, local email+password, JWT, admin seed, `app_logs` ring buffer + structlog middleware, basic Admin Logs tab showing live entries. |
| M2 | Upload + Canvas | Presentations/versions/slides, single-HTML upload, local storage driver, assets router + CSP + signed URLs + `probe.js`, `SlideFrame`, `PresentationPage` with TopNav + 16:9 elevated canvas + floating ActionBar + prev/next. |
| M3 | Comments (manual refresh) | Threads + comments tables, endpoints, FeedbackSidebar, CommentMarker overlay, comment-mode crosshair, refresh button. |
| M4 | Share + Export | Share links + exchange flow, ShareModal, ExportModal, Playwright PDF exporter, `export_jobs` table + polling, single-HTML inliner, download route. Zip upload support added here so the inliner has something to chew on. |
| M5 | Admin page full | Jobs, Presentations, Users, Audit, Stats tabs. Filters + request-ID search on Logs. |
| M6 | Mobile + polish | vaul drawers below `md`, long-press comment flow, hide Export on mobile, large touch markers, Playwright mobile viewport tests. |
| M7 | Hardening | Zip-slip fuzz, CSP audit, rate limits, argon2 tuning, backup script, systemd unit files + nginx config, deploy runbook. |

Roadmap items (separate track, explicit in `docs/ROADMAP.md`): real-time via SSE, LiteLLM-based AI regen, Entra ID OIDC, Azure Blob driver, GitLab/GitHub sync.

## Critical Files to Create

Backend:
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/logging_conf.py`
- `backend/app/db/models/presentation.py` + siblings
- `backend/app/routers/{auth,presentations,versions,assets,comments,shares,exports,admin}.py`
- `backend/app/services/{upload,slide_manifest,pdf_export,html_inliner,shares,acl,admin_logs}.py`
- `backend/app/jobs/{background,export_runner,upload_runner}.py`
- `backend/app/storage/{base,local,azure_blob}.py`
- `backend/app/security/{jwt,passwords,csp,ratelimit}.py`
- `backend/app/probe/probe.js`
- `backend/alembic/versions/0001_init.py`
- `backend/app/tests/conftest.py` + factories + router tests

Frontend:
- `frontend/src/styles/tailwind.css` (Tailwind 4 `@theme`)
- `frontend/src/components/canvas/SlideFrame.tsx`
- `frontend/src/components/feedback/FeedbackSidebar.tsx`
- `frontend/src/components/share/ShareModal.tsx`
- `frontend/src/components/export/ExportModal.tsx`
- `frontend/src/components/admin/{AdminDashboard,LogsTable,JobsTable}.tsx`
- `frontend/src/pages/{LoginPage,FileManagerPage,PresentationPage,AdminPage,ShareEntryPage}.tsx`
- `frontend/src/lib/api/` (generated)
- `frontend/src/hooks/{usePresentation,useComments,useAdminLogs}.ts`

Root / LLM / ops:
- `CLAUDE.md`
- `.cursorrules`
- `justfile`
- `scripts/verify.sh`, `scripts/e2e_smoke.py`, `scripts/dev.sh`, `scripts/seed.py`
- `docs/{CONVENTIONS,RUNBOOK,PROBE_PROTOCOL,ROADMAP,SECURITY}.md`
- `docs/adr/0001…0003*.md`
- `deploy/systemd/promptdeck-api.service`
- `deploy/nginx/promptdeck.conf`
- `.github/workflows/verify.yml` (or `.gitlab-ci.yml`)

## Verification

Definition of done for v1: a user can log in, upload `sample_deck.html` or `sample_bundle.zip`, see the slides in the canvas, leave coordinate-pinned comments that persist and appear on refresh, click Share and hand a link to a colleague who can comment as a scoped viewer, export the deck to a single PDF or single self-contained HTML and download it, and an admin can open `/admin`, filter logs by request ID from a toast error, and find the exact event chain for any user action. `just verify` exits 0 with all sections green, including the end-to-end smoke script.
