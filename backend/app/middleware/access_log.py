from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from app.db.session import session_factory
from app.logging_channels import LogChannel, channel_logger
from app.services.app_logging import write_app_log
from app.services.audit import client_ip_from_request
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = channel_logger(LogChannel.http)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            log.exception("http.unhandled")
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            user = getattr(request.state, "user_id", None)
            path = request.url.path
            method = request.method
            log.info(
                "http.request",
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=latency_ms,
            )
            if status_code >= 500:
                log_level = "error"
            elif status_code >= 400:
                log_level = "warning"
            else:
                log_level = "info"
            payload: dict[str, str] = {}
            client_ip = client_ip_from_request(request)
            if client_ip:
                payload["client_ip"] = client_ip
            ua = request.headers.get("user-agent")
            if ua:
                payload["user_agent"] = ua[:240]
            try:
                async with session_factory()() as session:
                    await write_app_log(
                        session,
                        channel=LogChannel.http,
                        level=log_level,
                        event="http.request",
                        request_id=request_id,
                        user_id=user,
                        path=path,
                        method=method,
                        status_code=status_code,
                        latency_ms=latency_ms,
                        payload=payload or None,
                    )
            except Exception:
                log.exception("app_log.write_failed", path=path)
            if response is not None:
                response.headers["X-Request-ID"] = request_id

        if response is None:
            raise RuntimeError("missing response")
        return response
