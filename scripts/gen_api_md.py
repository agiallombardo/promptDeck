#!/usr/bin/env python3
"""Emit docs/API.md from the committed OpenAPI snapshot (for LLM / human navigation)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENAPI = ROOT / "backend" / "openapi.json"
OUT = ROOT / "docs" / "API.md"


def main() -> None:
    data = json.loads(OPENAPI.read_text(encoding="utf-8"))
    paths = data.get("paths") or {}
    lines = [
        "# promptDeck API (generated)",
        "",
        "Regenerate with `just api-contract` after changing `backend/openapi.json`.",
        "",
        "| Method | Path | Summary |",
        "|--------|------|---------|",
    ]
    for path, item in sorted(paths.items()):
        if not isinstance(item, dict):
            continue
        for method, op in sorted(item.items()):
            if method not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(op, dict):
                continue
            summary = (op.get("summary") or op.get("operationId") or "").replace("|", "\\|")
            lines.append(f"| {method.upper()} | `{path}` | {summary} |")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
