from __future__ import annotations

import time
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation, PresentationVersion, Slide
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.deps import (
    Principal,
    get_current_user,
    get_presentation_owner,
    get_presentation_reader,
    get_principal,
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
    return _presentation_read(p)


@router.get("", response_model=PresentationListResponse)
async def list_presentations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationListResponse:
    q = select(Presentation).where(Presentation.deleted_at.is_(None))
    if user.role != UserRole.admin:
        q = q.where(Presentation.owner_id == user.id)
    q = q.order_by(Presentation.updated_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()
    return PresentationListResponse(items=[_presentation_read(p) for p in rows])


@router.get("/{presentation_id}", response_model=PresentationRead)
async def get_presentation_detail(
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_reader)],
) -> PresentationRead:
    result = await db.execute(
        select(Presentation)
        .where(Presentation.id == presentation.id)
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
    return _presentation_read(p, current_version=current)


@router.patch("/{presentation_id}", response_model=PresentationRead)
async def update_presentation(
    request: Request,
    body: PresentationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> PresentationRead:
    if body.title is not None:
        presentation.title = body.title
    if body.description is not None:
        presentation.description = body.description
    await db.commit()
    await db.refresh(presentation)
    await record_audit(
        db,
        actor_id=user.id,
        action="presentation.updated",
        target_kind="presentation",
        target_id=presentation.id,
        metadata={"title": presentation.title},
        client_ip=client_ip_from_request(request),
    )
    return _presentation_read(presentation)


@router.delete("/{presentation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presentation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> None:
    from datetime import UTC, datetime

    pres_id = presentation.id
    pres_title = presentation.title
    presentation.deleted_at = datetime.now(UTC)
    await db.commit()
    await record_audit(
        db,
        actor_id=user.id,
        action="presentation.deleted",
        target_kind="presentation",
        target_id=pres_id,
        metadata={"title": pres_title},
        client_ip=client_ip_from_request(request),
    )


@router.get("/{presentation_id}/embed", response_model=EmbedResponse)
async def embed_iframe(
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_reader)],
) -> EmbedResponse:
    if presentation.current_version_id is None:
        raise HTTPException(status_code=400, detail="No active version; upload HTML first")
    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None:
        raise HTTPException(status_code=404, detail="Current version not found")
    slide_rows = await db.execute(select(Slide).where(Slide.version_id == ver.id))
    slides = slide_rows.scalars().all()
    sub_id, role_str = principal.asset_identity()
    exp = int(time.time()) + settings.asset_url_ttl_seconds
    sig = sign_asset(
        settings,
        version_id=ver.id,
        user_id=sub_id,
        role=role_str,
        exp=exp,
    )
    qs = urlencode(
        {
            "exp": str(exp),
            "sig": sig,
            "sub": str(sub_id),
            "role": role_str,
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
