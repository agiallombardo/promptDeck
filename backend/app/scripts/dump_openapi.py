"""Write `backend/openapi.json` from the current FastAPI app (for CI contract tests)."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


def main() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    out = backend_root / "openapi.json"
    doc = app.openapi()
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
