from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import UTC, datetime


def encode_keyset_cursor(ts: datetime, row_id: uuid.UUID) -> str:
    t = ts.astimezone(UTC)
    payload = {"a": t.isoformat().replace("+00:00", "Z"), "i": str(row_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_keyset_cursor(raw: str | None) -> tuple[datetime, uuid.UUID] | None:
    if raw is None or not raw.strip():
        return None
    pad = "=" * (-len(raw) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + pad).decode())
        a = data["a"]
        i = data["i"]
        if not isinstance(a, str) or not isinstance(i, str):
            return None
        ts = datetime.fromisoformat(a.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        else:
            ts = ts.astimezone(UTC)
        return ts, uuid.UUID(i)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError, binascii.Error):
        return None
