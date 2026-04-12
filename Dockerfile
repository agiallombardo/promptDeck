# syntax=docker/dockerfile:1
# All-in-one API + SQLite + Vite static (optional STATIC_SITE_DIR). See docs/RUNBOOK.md.

FROM node:24-bookworm-slim AS frontend
WORKDIR /build
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM python:3.12-slim-bookworm AS backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
RUN uv run playwright install-deps chromium
RUN uv run playwright install chromium
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY --from=frontend /build/dist ./static/site
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
COPY scripts/bootstrap_users.py /app/scripts/bootstrap_users.py
COPY scripts/seed.py /app/scripts/seed.py
RUN chmod +x /docker-entrypoint.sh
ENV STATIC_SITE_DIR=/app/backend/static/site
EXPOSE 8005
ENTRYPOINT ["/docker-entrypoint.sh"]
