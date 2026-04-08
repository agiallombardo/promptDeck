# ADR 0001: Stack choices

## Status

Accepted

## Context

Internal corporate app: FastAPI + Postgres + React, LLM-maintainable codebase.

## Decision

- Backend: Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, structlog (logging in M1+).
- Frontend: React 18, Vite 5, TypeScript 5, Tailwind 4 (CSS-first `@theme`).
- Tooling: `uv` (Python), `pnpm` (Node), `just` for task entrypoints.

## Consequences

Single VM deployment without Redis/worker in v1; background work via FastAPI `BackgroundTasks`.
