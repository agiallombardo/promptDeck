from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.app_log import AppLog
from app.db.models.user import User
from app.db.session import get_db
from app.deps import require_admin
from app.logging_channels import LogChannel, channel_logger
from app.schemas.admin import AppLogListResponse, AppLogRead
from app.services.app_logging import write_app_log

router = APIRouter()
audit_log = channel_logger(LogChannel.audit)


@router.get("/logs", response_model=AppLogListResponse)
async def list_logs(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    level: str | None = None,
    channel: str | None = Query(
        default=None,
        description="Filter by channel (http, auth, audit, script)",
    ),
    request_id: str | None = None,
    user_id: uuid.UUID | None = None,
    since: datetime | None = None,
    cursor: int | None = Query(default=None, description="Use `id` of oldest row from prior page"),
) -> AppLogListResponse:
    stmt = select(AppLog).order_by(AppLog.id.desc())
    if level:
        stmt = stmt.where(AppLog.level == level)
    if channel:
        stmt = stmt.where(AppLog.logger == channel)
    if request_id:
        stmt = stmt.where(AppLog.request_id == request_id)
    if user_id:
        stmt = stmt.where(AppLog.user_id == user_id)
    if since:
        stmt = stmt.where(AppLog.ts >= since)
    if cursor is not None:
        stmt = stmt.where(AppLog.id < cursor)

    stmt = stmt.limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    next_cursor: int | None = None
    if len(rows) > limit:
        page = rows[:limit]
        next_cursor = page[-1].id
        rows = page

    audit_log.info(
        "audit.admin.logs.viewed",
        limit=limit,
        channel_filter=channel,
        result_count=len(rows),
    )
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.logs.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={
            "limit": limit,
            "channel_filter": channel,
            "result_count": len(rows),
        },
    )

    return AppLogListResponse(
        items=[AppLogRead.model_validate(r) for r in rows],
        next_cursor=next_cursor,
    )
