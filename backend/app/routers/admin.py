from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.app_log import AppLog
from app.db.models.audit_log import AuditLog
from app.db.models.deck_prompt_job import DeckPromptJob, DeckPromptJobStatus
from app.db.models.export_job import ExportJob
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User
from app.db.session import get_db
from app.deps import require_admin
from app.logging_channels import LogChannel, channel_logger
from app.rate_limit import limiter
from app.schemas.admin import (
    AdminDeckPromptJobListResponse,
    AdminDeckPromptJobRead,
    AdminEntraSettingsPatch,
    AdminEntraSettingsRead,
    AdminExportJobListResponse,
    AdminExportJobRead,
    AdminLlmSettingsPatch,
    AdminLlmSettingsRead,
    AdminPresentationListResponse,
    AdminPresentationRow,
    AdminSetupRead,
    AdminSmtpSettingsPatch,
    AdminSmtpSettingsRead,
    AdminSmtpTestRequest,
    AdminSmtpTestResponse,
    AdminStatsRead,
    AdminUserListResponse,
    AdminUserRead,
    AppLogListResponse,
    AppLogRead,
    AuditLogListResponse,
    AuditLogRead,
)
from app.services.app_logging import write_app_log
from app.services.audit import client_ip_from_request, record_audit
from app.services.entra_runtime import (
    entra_login_ready,
    load_system_settings_kv,
    persist_entra_system_settings,
    resolve_entra_oidc_config,
)
from app.services.llm_runtime import persist_litellm_system_settings, read_litellm_admin_settings
from app.services.smtp_runtime import (
    assert_smtp_config_valid,
    merge_smtp_settings_patch,
    persist_smtp_system_settings,
    resolve_smtp_config,
    send_smtp_message,
    smtp_password_configured,
    smtp_ready,
)

router = APIRouter()
audit_log = channel_logger(LogChannel.audit)


async def _admin_smtp_read(db: AsyncSession, settings: Settings) -> AdminSmtpSettingsRead:
    cfg = await resolve_smtp_config(db, settings)
    kv = await load_system_settings_kv(db)
    return AdminSmtpSettingsRead(
        smtp_enabled=cfg.enabled,
        smtp_host=cfg.host,
        smtp_port=cfg.port,
        smtp_username=cfg.username,
        smtp_from=cfg.from_address,
        smtp_starttls=cfg.starttls,
        smtp_implicit_tls=cfg.implicit_tls,
        smtp_validate_certs=cfg.validate_certs,
        smtp_auth_mode=cfg.auth_mode,
        smtp_password_configured=smtp_password_configured(settings, kv),
        smtp_password_stored_encrypted=True,
        smtp_ready=smtp_ready(cfg),
    )


async def _admin_entra_read(db: AsyncSession, settings: Settings) -> AdminEntraSettingsRead:
    cfg = await resolve_entra_oidc_config(db, settings)
    kv = await load_system_settings_kv(db)
    secret_ok = bool(settings.entra_client_secret) or bool(
        kv.get("entra_client_secret_encrypted", "").strip()
    )
    return AdminEntraSettingsRead(
        entra_enabled=cfg.enabled,
        entra_tenant_id=cfg.tenant_id,
        entra_client_id=cfg.client_id,
        entra_client_secret_configured=secret_ok,
        entra_authority_host=cfg.authority_host,
        public_api_url=settings.public_api_url,
        entra_redirect_uri=settings.entra_redirect_uri,
    )


@router.get("/setup", response_model=AdminSetupRead)
async def admin_setup(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminSetupRead:
    _ = admin_user
    cfg = await resolve_entra_oidc_config(db, settings)
    kv = await load_system_settings_kv(db)
    secret_db = bool(kv.get("entra_client_secret_encrypted", "").strip())
    smtp_cfg = await resolve_smtp_config(db, settings)
    return AdminSetupRead(
        local_password_auth_enabled=settings.local_password_auth_enabled,
        entra_enabled=settings.entra_enabled,
        entra_tenant_id_configured=(
            bool(settings.entra_tenant_id) or bool(kv.get("entra_tenant_id"))
        ),
        entra_client_id_configured=(
            bool(settings.entra_client_id) or bool(kv.get("entra_client_id"))
        ),
        entra_client_secret_configured=bool(settings.entra_client_secret) or secret_db,
        entra_login_ready=entra_login_ready(cfg),
        smtp_enabled=smtp_cfg.enabled,
        smtp_ready=smtp_ready(smtp_cfg),
        public_app_url=settings.public_app_url,
        public_api_url=settings.public_api_url,
        entra_redirect_uri=settings.entra_redirect_uri,
    )


@router.get("/settings/entra", response_model=AdminEntraSettingsRead)
async def admin_entra_settings_get(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminEntraSettingsRead:
    _ = admin_user
    return await _admin_entra_read(db, settings)


@router.patch("/settings/entra", response_model=AdminEntraSettingsRead)
async def admin_entra_settings_patch(
    request: Request,
    body: AdminEntraSettingsPatch,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminEntraSettingsRead:
    dump = body.model_dump()
    has_change = body.clear_entra_client_secret or any(
        dump[k] is not None for k in dump if k not in ("clear_entra_client_secret",)
    )
    if has_change:
        await persist_entra_system_settings(
            db,
            settings,
            enabled=body.entra_enabled,
            tenant_id=body.entra_tenant_id,
            client_id=body.entra_client_id,
            client_secret=body.entra_client_secret,
            clear_client_secret=body.clear_entra_client_secret,
            authority_host=body.entra_authority_host,
        )
        await record_audit(
            db,
            actor_id=admin_user.id,
            action="admin.entra_settings.updated",
            metadata={"keys": [k for k, v in dump.items() if v is not None]},
            client_ip=client_ip_from_request(request),
        )
    return await _admin_entra_read(db, settings)


@router.get("/settings/smtp", response_model=AdminSmtpSettingsRead)
async def admin_smtp_settings_get(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminSmtpSettingsRead:
    _ = admin_user
    return await _admin_smtp_read(db, settings)


@router.patch("/settings/smtp", response_model=AdminSmtpSettingsRead)
async def admin_smtp_settings_patch(
    request: Request,
    body: AdminSmtpSettingsPatch,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminSmtpSettingsRead:
    dump = body.model_dump()
    has_change = body.clear_smtp_password or any(
        dump[k] is not None for k in dump if k not in ("clear_smtp_password",)
    )
    if has_change:
        current = await resolve_smtp_config(db, settings)
        merged = merge_smtp_settings_patch(current, body)
        try:
            assert_smtp_config_valid(merged)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        from_str = str(body.smtp_from) if body.smtp_from is not None else None
        await persist_smtp_system_settings(
            db,
            settings,
            enabled=body.smtp_enabled,
            host=body.smtp_host,
            port=body.smtp_port,
            username=body.smtp_username,
            from_address=from_str,
            starttls=body.smtp_starttls,
            implicit_tls=body.smtp_implicit_tls,
            validate_certs=body.smtp_validate_certs,
            auth_mode=body.smtp_auth_mode,
            password=body.smtp_password,
            clear_password=body.clear_smtp_password,
        )
        await record_audit(
            db,
            actor_id=admin_user.id,
            action="admin.smtp_settings.updated",
            metadata={"keys": [k for k, v in dump.items() if v is not None]},
            client_ip=client_ip_from_request(request),
        )
    return await _admin_smtp_read(db, settings)


@router.get("/settings/llm", response_model=AdminLlmSettingsRead)
async def admin_llm_settings_get(
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminLlmSettingsRead:
    _ = admin_user
    return await read_litellm_admin_settings(db, settings)


@router.patch("/settings/llm", response_model=AdminLlmSettingsRead)
async def admin_llm_settings_patch(
    request: Request,
    body: AdminLlmSettingsPatch,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminLlmSettingsRead:
    dump = body.model_dump()
    has_change = (
        body.clear_litellm_api_key
        or body.clear_litellm_api_base
        or dump.get("litellm_api_base") is not None
        or dump.get("litellm_api_key") is not None
    )
    if has_change:
        try:
            await persist_litellm_system_settings(
                db,
                settings,
                api_base=None if body.clear_litellm_api_base else body.litellm_api_base,
                api_key=body.litellm_api_key,
                clear_api_key=body.clear_litellm_api_key,
                clear_api_base=body.clear_litellm_api_base,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        llm_meta_keys = [k for k, v in dump.items() if v is not None and k != "litellm_api_key"]
        await record_audit(
            db,
            actor_id=admin_user.id,
            action="admin.llm_settings.updated",
            metadata={"keys": llm_meta_keys},
            client_ip=client_ip_from_request(request),
        )
    return await read_litellm_admin_settings(db, settings)


@router.post("/settings/smtp/test", response_model=AdminSmtpTestResponse)
async def admin_smtp_test(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    body: Annotated[AdminSmtpTestRequest | None, Body()] = None,
) -> AdminSmtpTestResponse:
    payload = body or AdminSmtpTestRequest()
    cfg = await resolve_smtp_config(db, settings)
    if not smtp_ready(cfg):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP is disabled or missing host, From address, or password",
        )
    to_addr = str(payload.to) if payload.to is not None else admin_user.email
    subject = "promptDeck SMTP test"
    text = (
        "This is a test message from the promptDeck admin console.\n\n"
        "If you received it, outbound SMTP (e.g. Microsoft 365) is configured correctly."
    )
    try:
        await send_smtp_message(cfg, to_addrs=[to_addr], subject=subject, text_body=text)
    except Exception as e:
        audit_log.warning("admin.smtp.test.failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMTP send failed: {e}",
        ) from e
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.smtp.test.sent",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"to": to_addr},
    )
    await record_audit(
        db,
        actor_id=admin_user.id,
        action="admin.smtp.test.sent",
        metadata={"to": to_addr},
        client_ip=client_ip_from_request(request),
    )
    await db.commit()
    return AdminSmtpTestResponse(to=to_addr)


@router.get("/logs", response_model=AppLogListResponse)
@limiter.limit("30/minute")
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
    event_contains: str | None = Query(
        default=None,
        max_length=128,
        description="Substring match on `event` (e.g. auth.login, http.request)",
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
    if event_contains:
        stmt = stmt.where(AppLog.event.contains(event_contains))
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
        event_contains_filter=event_contains,
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
            "event_contains": event_contains,
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


def _deck_prompt_prompt_preview(prompt: str, max_len: int = 120) -> str:
    s = prompt.replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


@router.get("/deck-prompt-jobs", response_model=AdminDeckPromptJobListResponse)
async def list_deck_prompt_jobs_admin(
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
) -> AdminDeckPromptJobListResponse:
    stmt = (
        select(DeckPromptJob, Presentation.title, User.email)
        .join(Presentation, DeckPromptJob.presentation_id == Presentation.id)
        .join(User, DeckPromptJob.created_by == User.id)
        .order_by(DeckPromptJob.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="audit.admin.deck_prompt_jobs.viewed",
        request_id=getattr(request.state, "request_id", None),
        user_id=admin_user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=200,
        latency_ms=None,
        payload={"result_count": len(rows)},
    )
    items = [
        AdminDeckPromptJobRead(
            id=job.id,
            presentation_id=job.presentation_id,
            presentation_title=title,
            source_version_id=job.source_version_id,
            status=str(job.status),
            progress=job.progress,
            error=job.error,
            result_version_id=job.result_version_id,
            prompt_preview=_deck_prompt_prompt_preview(job.prompt),
            llm_model=job.llm_model,
            prompt_tokens=job.prompt_tokens,
            completion_tokens=job.completion_tokens,
            total_tokens=job.total_tokens,
            created_by=job.created_by,
            creator_email=email,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        for job, title, email in rows
    ]
    return AdminDeckPromptJobListResponse(items=items)


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
    deck_prompt_jobs = await _count(DeckPromptJob)
    deck_prompt_jobs_24h = await _count(DeckPromptJob, DeckPromptJob.created_at >= since)

    sum_stmt = select(
        func.coalesce(func.sum(DeckPromptJob.prompt_tokens), 0),
        func.coalesce(func.sum(DeckPromptJob.completion_tokens), 0),
        func.coalesce(func.sum(DeckPromptJob.total_tokens), 0),
    ).where(
        DeckPromptJob.finished_at.is_not(None),
        DeckPromptJob.finished_at >= since,
        DeckPromptJob.status == DeckPromptJobStatus.succeeded,
    )
    sum_row = (await db.execute(sum_stmt)).one()
    llm_prompt_tokens_24h = int(sum_row[0] or 0)
    llm_completion_tokens_24h = int(sum_row[1] or 0)
    llm_total_tokens_24h = int(sum_row[2] or 0)

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
        deck_prompt_jobs=deck_prompt_jobs,
        deck_prompt_jobs_24h=deck_prompt_jobs_24h,
        llm_prompt_tokens_24h=llm_prompt_tokens_24h,
        llm_completion_tokens_24h=llm_completion_tokens_24h,
        llm_total_tokens_24h=llm_total_tokens_24h,
        audit_events_24h=audit_events_24h,
        app_log_rows_24h=app_log_rows_24h,
    )
