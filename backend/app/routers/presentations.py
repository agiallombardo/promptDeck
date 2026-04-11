from __future__ import annotations

import time
import uuid
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation, PresentationVersion, Slide
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
from app.schemas.presentation import (
    EmbedResponse,
    PresentationCreate,
    PresentationListResponse,
    PresentationRead,
    PresentationUpdate,
    SlideRead,
    VersionRead,
)
from app.security.asset_signing import sign_asset
from app.services.acl import PresentationAccess
from app.services.audit import client_ip_from_request, record_audit

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
        description=p.description,
        current_version_id=p.current_version_id,
        created_at=p.created_at,
        updated_at=p.updated_at,
        current_user_role=access,
        current_version=cv,
    )


@router.post("", response_model=PresentationRead, status_code=status.HTTP_201_CREATED)
async def create_presentation(
    body: PresentationCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationRead:
    p = Presentation(owner_id=user.id, title=body.title, description=body.description)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    access = PresentationAccess.admin if user.role == UserRole.admin else PresentationAccess.owner
    return _presentation_read(p, access=access)


@router.get("", response_model=PresentationListResponse)
async def list_presentations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationListResponse:
    if user.role == UserRole.admin:
        stmt = (
            select(Presentation)
            .where(Presentation.deleted_at.is_(None))
            .order_by(Presentation.updated_at.desc())
        )
        rows = (await db.execute(stmt)).scalars().all()
        return PresentationListResponse(
            items=[_presentation_read(row, access=PresentationAccess.admin) for row in rows]
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
        .group_by(Presentation.id)
        .order_by(Presentation.updated_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    items: list[PresentationRead] = []
    for row, rank in rows:
        access = PresentationAccess.user
        if int(rank or 1) >= 3:
            access = PresentationAccess.owner
        elif int(rank or 1) == 2:
            access = PresentationAccess.editor
        items.append(_presentation_read(row, access=access))
    return PresentationListResponse(items=items)


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
    if presentation.current_version_id is None:
        raise HTTPException(status_code=400, detail="No active version; upload HTML first")
    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None:
        raise HTTPException(status_code=404, detail="Current version not found")
    slide_rows = await db.execute(select(Slide).where(Slide.version_id == ver.id))
    slides = slide_rows.scalars().all()
    exp = int(time.time()) + settings.asset_url_ttl_seconds
    sig_sub = grant.user.id if grant.user is not None else uuid.uuid4()
    sig = sign_asset(
        settings,
        version_id=ver.id,
        user_id=sig_sub,
        role=grant.access.value,
        exp=exp,
    )
    qs = urlencode(
        {
            "exp": str(exp),
            "sig": sig,
            "sub": str(sig_sub),
            "role": grant.access.value,
        }
    )
    parts = ver.entry_path.replace("\\", "/").split("/")
    path_q = "/".join(quote(p, safe="") for p in parts if p)
    base = settings.public_app_url.rstrip("/")
    iframe_src = f"{base}/a/{ver.id}/{path_q}?{qs}"
    return EmbedResponse(
        iframe_src=iframe_src,
        version_id=ver.id,
        slide_count=len(slides),
    )
