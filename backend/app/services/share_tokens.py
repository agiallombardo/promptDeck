from __future__ import annotations

import hashlib


def hash_share_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
