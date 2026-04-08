"""Helpers for asserting structured app log rows in tests."""

from __future__ import annotations

from app.db.models.app_log import AppLog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def assert_logged(
    session: AsyncSession,
    *,
    event: str,
    level: str = "info",
    min_count: int = 1,
) -> None:
    result = await session.execute(
        select(func.count())
        .select_from(AppLog)
        .where(AppLog.event == event, AppLog.level == level),
    )
    n = int(result.scalar_one())
    assert n >= min_count, (
        f"app_logs: expected at least {min_count} row(s) for event={event!r} "
        f"level={level!r}, got {n}"
    )
