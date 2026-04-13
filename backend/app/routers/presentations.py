from __future__ import annotations

import time
import uuid
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db.models.deck_prompt_job import DeckPromptJob, DeckPromptJobStatus, DeckPromptJobType
from app.db.models.presentation import Presentation, PresentationKind, PresentationVersion, Slide
from app.db.models.presentation_member import PresentationMember, PresentationMemberRole
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.deps import (
    PresentationGrant,
    get_current_user,
    get_presentation_editor,
    get_presentation_owner,
    get_presentation_reader,
)
from app.jobs.deck_prompt_runner import run_deck_prompt_job
from app.rate_limit import limiter
from app.schemas.deck_prompt import DeckPromptJobRead
from app.schemas.presentation import (
    DiagramDocumentRead,
    DiagramDocumentWrite,
    DiagramThumbnailResponse,
    EmbedResponse,
    PresentationCreate,
    PresentationGenerateFromPromptCreate,
    PresentationGenerateFromPromptResponse,
    PresentationListResponse,
    PresentationRead,
    PresentationUpdate,
    SlideRead,
    VersionRead,
)
from app.security.asset_signing import sign_asset
from app.services.acl import PresentationAccess
from app.services.audit import client_ip_from_request, record_audit
from app.services.diagram_version import (
    persist_new_diagram_version,
    read_diagram_document,
    starter_diagram_document,
)
from app.services.keyset_cursor import decode_keyset_cursor, encode_keyset_cursor
from app.services.llm_runtime import LlmNotConfiguredError, resolve_deck_llm_credentials
from app.services.single_html_version import persist_new_single_html_version
from app.services.starter_deck_html import STARTER_DECK_HTML_BYTES

router = APIRouter(prefix="/presentations", tags=["presentations"])


def _version_read(ver: PresentationVersion) -> VersionRead:
    slides = sorted(ver.slides, key=lambda s: s.slide_index)
    return VersionRead(
        id=ver.id,
        presentation_id=ver.presentation_id,
        version_number=ver.version_number,
        origin=ver.origin,
        storage_kind=ver.storage_kind,
        entry_path=ver.entry_path,
        sha256=ver.sha256,
        size_bytes=ver.size_bytes,
        created_at=ver.created_at,
        slides=[SlideRead.model_validate(s) for s in slides],
    )


def _presentation_read(
    p: Presentation,
    *,
    access: PresentationAccess | None,
    current_version: PresentationVersion | None = None,
) -> PresentationRead:
    cv = _version_read(current_version) if current_version is not None else None
    return PresentationRead(
        id=p.id,
        owner_id=p.owner_id,
        title=p.title,
        kind=str(p.kind),
        description=p.description,
        current_version_id=p.current_version_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
        current_user_role=access,
        current_version=cv,
    )


def _signed_asset_url(
    *,
    settings: Settings,
    version_id: uuid.UUID,
    rel_path: str,
    role: str,
    sub: uuid.UUID,
) -> str:
    exp = int(time.time()) + settings.asset_url_ttl_seconds
    sig = sign_asset(
        settings,
        version_id=version_id,
        user_id=sub,
        role=role,
        exp=exp,
    )
    qs = urlencode({"exp": str(exp), "sig": sig, "sub": str(sub), "role": role})
    parts = rel_path.replace("\\", "/").split("/")
    path_q = "/".join(quote(p, safe="") for p in parts if p)
    base = settings.public_app_url.rstrip("/")
    return f"{base}/a/{version_id}/{path_q}?{qs}"


@router.post("", response_model=PresentationRead, status_code=status.HTTP_201_CREATED)
async def create_presentation(
    body: PresentationCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PresentationRead:
    p = Presentation(
        owner_id=user.id,
        title=body.title,
        kind=PresentationKind(body.kind),
        description=body.description,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    current_version: PresentationVersion | None = None
    if p.kind == PresentationKind.diagram:
        current_version = await persist_new_diagram_version(
            settings=settings,
            db=db,
            presentation_id=p.id,
            diagram_document=starter_diagram_document(),
            origin="diagram_starter",
            created_by=user.id,
        )
        await db.refresh(p)
    access = PresentationAccess.admin if user.role == UserRole.admin else PresentationAccess.owner
    return _presentation_read(p, access=access, current_version=current_version)


@router.post(
    "/generate-from-prompt",
    response_model=PresentationGenerateFromPromptResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def generate_presentation_from_prompt(
    request: Request,
    body: PresentationGenerateFromPromptCreate,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PresentationGenerateFromPromptResponse:
    try:
        await resolve_deck_llm_credentials(db, settings, user.id)
    except LlmNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    p = Presentation(
        owner_id=user.id,
        title=body.title.strip(),
        kind=PresentationKind.deck,
        description=body.description,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)

    ver = await persist_new_single_html_version(
        settings=settings,
        db=db,
        presentation_id=p.id,
        html_bytes=STARTER_DECK_HTML_BYTES,
        entry_filename="index.html",
        origin="ai_starter",
        created_by=user.id,
    )
    await db.refresh(p)

    result_cv = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.id == ver.id)
        .options(selectinload(PresentationVersion.slides))
    )
    cv_row = result_cv.scalar_one()
    access = PresentationAccess.admin if user.role == UserRole.admin else PresentationAccess.owner
    pres_read = _presentation_read(p, access=access, current_version=cv_row)

    job = DeckPromptJob(
        presentation_id=p.id,
        source_version_id=ver.id,
        prompt=body.prompt.strip(),
        job_type=DeckPromptJobType.deck_generate,
        is_generation=True,
        status=DeckPromptJobStatus.queued,
        progress=0,
        status_message="Queued",
        created_by=user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await record_audit(
        db,
        actor_id=user.id,
        action="presentation.generate_from_prompt.created",
        target_kind="deck_prompt_job",
        target_id=job.id,
        metadata={
            "presentation_id": str(p.id),
            "job_id": str(job.id),
            "source_version_id": str(ver.id),
        },
        client_ip=client_ip_from_request(request),
    )

    background_tasks.add_task(run_deck_prompt_job, job.id)
    return PresentationGenerateFromPromptResponse(
        presentation=pres_read,
        job=DeckPromptJobRead.model_validate(job),
    )


@router.post(
    "/generate-diagram-from-prompt",
    response_model=PresentationGenerateFromPromptResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def generate_diagram_from_prompt(
    request: Request,
    body: PresentationGenerateFromPromptCreate,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PresentationGenerateFromPromptResponse:
    try:
        await resolve_deck_llm_credentials(db, settings, user.id)
    except LlmNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    p = Presentation(
        owner_id=user.id,
        title=body.title.strip(),
        kind=PresentationKind.diagram,
        description=body.description,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)

    ver = await persist_new_diagram_version(
        settings=settings,
        db=db,
        presentation_id=p.id,
        diagram_document=starter_diagram_document(),
        origin="ai_starter",
        created_by=user.id,
    )
    await db.refresh(p)

    result_cv = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.id == ver.id)
        .options(selectinload(PresentationVersion.slides))
    )
    cv_row = result_cv.scalar_one()
    access = PresentationAccess.admin if user.role == UserRole.admin else PresentationAccess.owner
    pres_read = _presentation_read(p, access=access, current_version=cv_row)

    job = DeckPromptJob(
        presentation_id=p.id,
        source_version_id=ver.id,
        prompt=body.prompt.strip(),
        job_type=DeckPromptJobType.diagram_generate,
        is_generation=True,
        status=DeckPromptJobStatus.queued,
        progress=0,
        status_message="Queued",
        created_by=user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await record_audit(
        db,
        actor_id=user.id,
        action="presentation.generate_diagram_from_prompt.created",
        target_kind="deck_prompt_job",
        target_id=job.id,
        metadata={
            "presentation_id": str(p.id),
            "job_id": str(job.id),
            "source_version_id": str(ver.id),
        },
        client_ip=client_ip_from_request(request),
    )

    background_tasks.add_task(run_deck_prompt_job, job.id)
    return PresentationGenerateFromPromptResponse(
        presentation=pres_read,
        job=DeckPromptJobRead.model_validate(job),
    )


@router.get("", response_model=PresentationListResponse)
async def list_presentations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(description="Keyset pagination cursor")] = None,
) -> PresentationListResponse:
    pair = decode_keyset_cursor(cursor)
    if cursor is not None and cursor.strip() and pair is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor")
    fetch = limit + 1

    if user.role == UserRole.admin:
        stmt = select(Presentation).where(Presentation.deleted_at.is_(None))
        if pair:
            cts, cid = pair
            stmt = stmt.where(
                or_(
                    Presentation.updated_at < cts,
                    and_(Presentation.updated_at == cts, Presentation.id < cid),
                )
            )
        stmt = stmt.order_by(Presentation.updated_at.desc(), Presentation.id.desc()).limit(fetch)
        rows = (await db.execute(stmt)).scalars().all()
        page = rows[:limit]
        next_c = None
        if len(rows) > limit:
            tail = page[-1]
            next_c = encode_keyset_cursor(tail.updated_at, tail.id)
        return PresentationListResponse(
            items=[_presentation_read(row, access=PresentationAccess.admin) for row in page],
            next_cursor=next_c,
        )

    join_cond = and_(
        PresentationMember.presentation_id == Presentation.id,
        PresentationMember.revoked_at.is_(None),
        or_(
            PresentationMember.user_id == user.id,
            and_(
                PresentationMember.principal_tenant_id == user.entra_tenant_id,
                PresentationMember.principal_entra_object_id == user.entra_object_id,
            ),
        ),
    )
    access_rank = case(
        (Presentation.owner_id == user.id, 3),
        (PresentationMember.role == PresentationMemberRole.editor, 2),
        else_=1,
    )
    stmt = (
        select(Presentation, func.max(access_rank).label("access_rank"))
        .outerjoin(PresentationMember, join_cond)
        .where(Presentation.deleted_at.is_(None))
        .where(or_(Presentation.owner_id == user.id, PresentationMember.id.is_not(None)))
    )
    if pair:
        cts, cid = pair
        stmt = stmt.where(
            or_(
                Presentation.updated_at < cts,
                and_(Presentation.updated_at == cts, Presentation.id < cid),
            )
        )
    stmt = (
        stmt.group_by(Presentation.id)
        .order_by(Presentation.updated_at.desc(), Presentation.id.desc())
        .limit(fetch)
    )
    rows = (await db.execute(stmt)).all()
    page_rows = rows[:limit]
    items: list[PresentationRead] = []
    for row, rank in page_rows:
        access = PresentationAccess.user
        if int(rank or 1) >= 3:
            access = PresentationAccess.owner
        elif int(rank or 1) == 2:
            access = PresentationAccess.editor
        items.append(_presentation_read(row, access=access))
    next_c = None
    if len(rows) > limit and page_rows:
        tail = page_rows[-1][0]
        next_c = encode_keyset_cursor(tail.updated_at, tail.id)
    return PresentationListResponse(items=items, next_cursor=next_c)


@router.get("/{presentation_id}", response_model=PresentationRead)
async def get_presentation_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
) -> PresentationRead:
    result = await db.execute(
        select(Presentation)
        .where(Presentation.id == grant.presentation.id)
        .options(
            selectinload(Presentation.versions).selectinload(PresentationVersion.slides),
        )
    )
    p = result.scalar_one()
    current: PresentationVersion | None = None
    if p.current_version_id is not None:
        for v in p.versions:
            if v.id == p.current_version_id:
                current = v
                break
    return _presentation_read(p, access=grant.access, current_version=current)


@router.patch("/{presentation_id}", response_model=PresentationRead)
async def update_presentation(
    request: Request,
    body: PresentationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationRead:
    presentation = grant.presentation
    if body.title is not None:
        presentation.title = body.title
    if body.description is not None:
        presentation.description = body.description
    await db.commit()
    await db.refresh(presentation)
    await record_audit(
        db,
        actor_id=grant.user.id if grant.user is not None else None,
        action="presentation.updated",
        target_kind="presentation",
        target_id=presentation.id,
        metadata={"title": presentation.title},
        client_ip=client_ip_from_request(request),
    )
    return _presentation_read(presentation, access=grant.access)


@router.delete("/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presentation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_owner)],
) -> None:
    from datetime import UTC, datetime

    pres_id = grant.presentation.id
    pres_title = grant.presentation.title
    grant.presentation.deleted_at = datetime.now(UTC)
    await db.commit()
    await record_audit(
        db,
        actor_id=grant.user.id if grant.user is not None else None,
        action="presentation.deleted",
        target_kind="presentation",
        target_id=pres_id,
        metadata={"title": pres_title},
        client_ip=client_ip_from_request(request),
    )


@router.get("/{presentation_id}/embed", response_model=EmbedResponse)
async def embed_iframe(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
) -> EmbedResponse:
    presentation = grant.presentation
    if presentation.kind == PresentationKind.diagram:
        raise HTTPException(status_code=400, detail="Diagram presentations do not use iframe embed")
    if presentation.current_version_id is None:
        raise HTTPException(status_code=400, detail="No active version; upload HTML first")
    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None:
        raise HTTPException(status_code=404, detail="Current version not found")
    slide_rows = await db.execute(select(Slide).where(Slide.version_id == ver.id))
    slides = slide_rows.scalars().all()
    sig_sub = grant.user.id if grant.user is not None else uuid.uuid4()
    iframe_src = _signed_asset_url(
        settings=settings,
        version_id=ver.id,
        rel_path=ver.entry_path,
        role=grant.access.value,
        sub=sig_sub,
    )
    return EmbedResponse(
        iframe_src=iframe_src,
        version_id=ver.id,
        slide_count=len(slides),
    )


@router.get("/{presentation_id}/diagram", response_model=DiagramDocumentRead)
async def get_diagram_document(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
    version_id: Annotated[uuid.UUID | None, Query(description="Optional version id")] = None,
) -> DiagramDocumentRead:
    presentation = grant.presentation
    if presentation.kind != PresentationKind.diagram:
        raise HTTPException(status_code=400, detail="Presentation is not a diagram")
    vid = version_id or presentation.current_version_id
    if vid is None:
        raise HTTPException(status_code=400, detail="No active version")
    ver = await db.get(PresentationVersion, vid)
    if ver is None or ver.presentation_id != presentation.id:
        raise HTTPException(status_code=404, detail="Version not found")
    if ver.storage_kind != "xyflow_json":
        raise HTTPException(status_code=400, detail="Version is not a diagram document")
    doc = read_diagram_document(settings, ver)
    return DiagramDocumentRead(version_id=ver.id, document=doc)


@router.get("/{presentation_id}/diagram/thumbnail", response_model=DiagramThumbnailResponse)
async def get_diagram_thumbnail(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
) -> DiagramThumbnailResponse:
    presentation = grant.presentation
    if presentation.kind != PresentationKind.diagram:
        raise HTTPException(status_code=400, detail="Presentation is not a diagram")
    if presentation.current_version_id is None:
        raise HTTPException(status_code=400, detail="No active version")
    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None or ver.presentation_id != presentation.id:
        raise HTTPException(status_code=404, detail="Version not found")
    sig_sub = grant.user.id if grant.user is not None else uuid.uuid4()
    png_src = _signed_asset_url(
        settings=settings,
        version_id=ver.id,
        rel_path="thumbnail.png",
        role=grant.access.value,
        sub=sig_sub,
    )
    jpg_src = _signed_asset_url(
        settings=settings,
        version_id=ver.id,
        rel_path="thumbnail.jpg",
        role=grant.access.value,
        sub=sig_sub,
    )
    return DiagramThumbnailResponse(version_id=ver.id, png_src=png_src, jpg_src=jpg_src)


@router.put("/{presentation_id}/diagram", response_model=DiagramDocumentRead)
async def save_diagram_document(
    request: Request,
    body: DiagramDocumentWrite,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> DiagramDocumentRead:
    presentation = grant.presentation
    if presentation.kind != PresentationKind.diagram:
        raise HTTPException(status_code=400, detail="Presentation is not a diagram")

    ver = await persist_new_diagram_version(
        settings=settings,
        db=db,
        presentation_id=presentation.id,
        diagram_document=body.document,
        origin="diagram_edit",
        created_by=grant.user.id if grant.user is not None else None,
    )
    await record_audit(
        db,
        actor_id=grant.user.id if grant.user is not None else None,
        action="presentation.diagram.saved",
        target_kind="presentation_version",
        target_id=ver.id,
        metadata={"presentation_id": str(presentation.id), "version_number": ver.version_number},
        client_ip=client_ip_from_request(request),
    )
    doc = read_diagram_document(settings, ver)
    return DiagramDocumentRead(version_id=ver.id, document=doc)
