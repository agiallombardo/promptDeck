# syntax=docker/dockerfile:1
# All-in-one image: FastAPI + SQLite-oriented defaults + Vite static UI + Playwright/Chromium for export.
# See docs/RUNBOOK.md § Docker deployment.

FROM node:24-bookworm AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
COPY frontend/ ./
RUN pnpm install --frozen-lockfile && pnpm run build

FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
COPY backend/ ./
RUN uv sync --frozen --no-dev \
    && uv run playwright install-deps chromium \
    && uv run playwright install chromium

COPY --from=frontend-build /app/frontend/dist ./static/site
COPY scripts/ /app/scripts/

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8005
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
