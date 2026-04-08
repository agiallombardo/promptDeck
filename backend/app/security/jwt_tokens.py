from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from app.config import Settings
from jwt.exceptions import InvalidTokenError

TokenKind = Literal["access", "refresh", "share_access"]


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    email: str,
    role: str,
) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(settings: Settings, *, user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(settings: Settings, token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def decode_token_typed(settings: Settings, token: str, expected: TokenKind) -> dict[str, Any]:
    try:
        data = decode_token(settings, token)
    except InvalidTokenError as e:
        raise ValueError("invalid token") from e
    if data.get("type") != expected:
        raise ValueError("wrong token type")
    return data


def create_share_access_token(
    settings: Settings,
    *,
    share_link_id: uuid.UUID,
    presentation_id: uuid.UUID,
    role: str,
    link_expires_at: datetime | None,
) -> str:
    """JWT for share-link viewers; bounded by link expiry and a 7-day cap."""
    now = datetime.now(UTC)
    cap = now + timedelta(days=7)
    if link_expires_at is not None:
        cap = min(cap, link_expires_at)
    exp = int(cap.timestamp())
    payload: dict[str, Any] = {
        "sub": str(share_link_id),
        "presentation_id": str(presentation_id),
        "role": role,
        "type": "share_access",
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
