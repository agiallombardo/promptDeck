#!/usr/bin/env bash
set -euo pipefail
cd /app/backend
uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8005
