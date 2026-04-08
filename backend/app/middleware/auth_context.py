from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from app.config import get_settings
from app.security.jwt_tokens import decode_token
from fastapi import Request, Response
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Attach `request.state.user_id` from Bearer access JWT when present (for access logs)."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.user_id = None
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            if token:
                try:
                    settings = get_settings()
                    data = decode_token(settings, token)
                    if data.get("type") == "access" and data.get("sub"):
                        request.state.user_id = uuid.UUID(str(data["sub"]))
                except (InvalidTokenError, ValueError, TypeError, KeyError):
                    request.state.user_id = None
        return await call_next(request)
