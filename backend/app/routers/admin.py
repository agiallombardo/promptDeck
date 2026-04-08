from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.app_log import AppLog
from app.db.models.audit_log import AuditLog
from app.db.models.export_job import ExportJob
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User
from app.db.session import get_db
from app.deps import require_admin
from app.logging_channels import LogChannel, channel_logger
from app.schemas.admin import (
    AdminExportJobListResponse,
    AdminExportJobRead,
    AdminPresentationListResponse,
    AdminPresentationRow,
    AdminStatsRead,
    AdminUserListResponse,
    AdminUserRead,
    AppLogListResponse,
    AppLogRead,
    AuditLogListResponse,
    AuditLogRead,
)
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
    path_prefix: str | None = Query(
        default=None,
        description="Only rows whose path starts with this prefix (e.g. /api/v1/admin)",
    ),
    cursor: int | None = Query(default=None, description="Use `id` of oldest row from prior page"),
) -> AppLogListResponse:
    stmt = select(AppLog).order_by(AppLog.id.desc())
    if level:
        stmt = stmt.where(AppLog.level == level)
    if channel is not None:
        try:
            LogChannel(channel)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel filter",
            ) from e
        stmt = stmt.where(AppLog.logger == channel)
    if request_id:
        stmt = stmt.where(AppLog.request_id == request_id)
    if user_id:
        stmt = stmt.where(AppLog.user_id == user_id)
    if since:
        stmt = stmt.where(AppLog.ts >= since)
    if path_prefix:
        stmt = stmt.where(AppLog.path.startswith(path_prefix))
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


@router.get("/audit", response_model=AuditLogListResponse)
async def list_audit(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
) -> AuditLogListResponse:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.audit.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"limit": limit, "result_count": len(rows)},
    )
    return AuditLogListResponse(items=[AuditLogRead.model_validate(r) for r in rows])


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=500),
) -> AdminUserListResponse:
    stmt = (
        select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).limit(limit)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.users.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"result_count": len(rows)},
    )
    items = [
        AdminUserRead(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role.value,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in rows
    ]
    return AdminUserListResponse(items=items)


@router.get("/presentations", response_model=AdminPresentationListResponse)
async def list_presentations_admin(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> AdminPresentationListResponse:
    vc = (
        select(
            PresentationVersion.presentation_id.label("pid"),
            func.count(PresentationVersion.id).label("cnt"),
        )
        .group_by(PresentationVersion.presentation_id)
        .subquery()
    )
    stmt = (
        select(Presentation, User.email, func.coalesce(vc.c.cnt, 0).label("version_count"))
        .join(User, Presentation.owner_id == User.id)
        .outerjoin(vc, vc.c.pid == Presentation.id)
        .where(Presentation.deleted_at.is_(None))
        .order_by(Presentation.updated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.presentations.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"result_count": len(rows)},
    )
    items = [
        AdminPresentationRow(
            id=p.id,
            title=p.title,
            owner_id=p.owner_id,
            owner_email=email,
            current_version_id=p.current_version_id,
            version_count=int(vcount or 0),
            updated_at=p.updated_at,
        )
        for p, email, vcount in rows
    ]
    return AdminPresentationListResponse(items=items)


@router.get("/jobs", response_model=AdminExportJobListResponse)
async def list_export_jobs_admin(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
) -> AdminExportJobListResponse:
    stmt = (
        select(ExportJob, Presentation.title)
        .join(Presentation, ExportJob.presentation_id == Presentation.id)
        .order_by(ExportJob.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.jobs.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"result_count": len(rows)},
    )
    items = [
        AdminExportJobRead(
            id=job.id,
            presentation_id=job.presentation_id,
            presentation_title=title,
            version_id=job.version_id,
            format=str(job.format),
            status=str(job.status),
            progress=job.progress,
            error=job.error,
            created_by=job.created_by,
            created_at=job.created_at,
            finished_at=job.finished_at,
        )
        for job, title in rows
    ]
    return AdminExportJobListResponse(items=items)


@router.get("/stats", response_model=AdminStatsRead)
async def admin_stats(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminStatsRead:
    since = datetime.now(UTC) - timedelta(hours=24)

    async def _count(model, *filters):
        q = select(func.count()).select_from(model)
        for f in filters:
            q = q.where(f)
        r = await db.execute(q)
        return int(r.scalar_one() or 0)

    users = await _count(User, User.deleted_at.is_(None))
    presentations = await _count(Presentation, Presentation.deleted_at.is_(None))
    versions = await _count(PresentationVersion)
    export_jobs = await _count(ExportJob)
    audit_events_24h = await _count(AuditLog, AuditLog.ts >= since)
    app_log_rows_24h = await _count(AppLog, AppLog.ts >= since)

    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.stats.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload=None,
    )

    return AdminStatsRead(
        users=users,
        presentations=presentations,
        versions=versions,
        export_jobs=export_jobs,
        audit_events_24h=audit_events_24h,
        app_log_rows_24h=app_log_rows_24h,
    )
