#!/usr/bin/env bash
# Logical backup of the promptDeck Postgres database (gzip SQL).
# Requires pg_dump and a libpq-compatible DATABASE_URL.
# Usage: DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/promptdeck ./scripts/backup_pg.sh [output_dir]
set -euo pipefail
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required." >&2
  exit 1
fi
OUT_DIR="${1:-./backups}"
mkdir -p "$OUT_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$OUT_DIR/promptdeck-${TS}.sql.gz"
# libpq expects postgresql://, not sqlalchemy+asyncpg.
PGURL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
pg_dump "$PGURL" --no-owner --format=plain | gzip -c >"$FILE"
echo "Wrote $FILE"
