from __future__ import annotations

import uuid
from typing import Any

import structlog
from app.db.models.app_log import AppLog
from app.logging_channels import LogChannel
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger("app.access")


async def write_app_log(
    session: AsyncSession,
    *,
    channel: LogChannel,
    level: str,
    event: str | None,
    request_id: str | None,
    user_id: uuid.UUID | None,
    path: str,
    method: str,
    status_code: int | None,
    latency_ms: int | None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Persist one row to `app_logs`; `channel` maps to the `logger` column."""
    row = AppLog(
        level=level,
        event=event,
        logger=channel.value,
        request_id=request_id,
        user_id=user_id,
        path=path,
        method=method,
        status_code=status_code,
        latency_ms=latency_ms,
        payload=payload,
    )
    session.add(row)
    await session.commit()
