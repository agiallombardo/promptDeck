"""Fail if committed OpenAPI snapshot drifts from the live app schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.main import app


def _normalize(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2)


def main() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    snapshot_path = backend_root / "openapi.json"
    current = app.openapi()
    if not snapshot_path.is_file():
        print(f"Missing snapshot: {snapshot_path}", file=sys.stderr)
        sys.exit(1)
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if _normalize(current) != _normalize(expected):
        print("OpenAPI snapshot is stale. Regenerate with:", file=sys.stderr)
        print("  cd backend && uv run python -m app.scripts.dump_openapi", file=sys.stderr)
        sys.exit(1)
    print("OpenAPI snapshot OK")


if __name__ == "__main__":
    main()
