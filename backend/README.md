# promptDeck backend

FastAPI application. See repo root `CLAUDE.md` for commands.

Postgres: from this directory, `uv run alembic upgrade head` (or repo root `just db-migrate`) applies all migrations. On an empty database, one run creates the full schema—see `docs/RUNBOOK.md`.
