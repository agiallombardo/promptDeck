from __future__ import annotations

import hashlib
import hmac
import time
import uuid

from app.config import Settings


def _msg(version_id: uuid.UUID, exp: int, user_id: uuid.UUID, role: str) -> bytes:
    return f"{version_id}|{exp}|{user_id}|{role}".encode()


def sign_asset(
    settings: Settings,
    *,
    version_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    exp: int,
) -> str:
    digest = hmac.new(
        settings.asset_signing_secret_bytes(),
        _msg(version_id, exp, user_id, role),
        hashlib.sha256,
    ).hexdigest()
    return digest


def verify_asset(
    settings: Settings,
    *,
    version_id: uuid.UUID,
    exp: int,
    sig: str,
    user_id: uuid.UUID,
    role: str,
) -> bool:
    if exp < int(time.time()):
        return False
    expected = sign_asset(settings, version_id=version_id, user_id=user_id, role=role, exp=exp)
    return hmac.compare_digest(expected, sig)
