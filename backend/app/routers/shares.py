from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation
from app.db.models.share_link import ShareLink
from app.db.session import get_db
from app.deps import PresentationGrant, get_presentation_editor
from app.rate_limit import limiter
from app.schemas.share import (
    ShareLinkCreate,
    ShareLinkCreateResponse,
    ShareLinkExchangeRequest,
    ShareLinkExchangeResponse,
    ShareLinkListResponse,
    ShareLinkRead,
)
from app.security.jwt_tokens import create_share_access_token
from app.services.audit import client_ip_from_request, record_audit
from app.services.share_tokens import hash_share_token

router = APIRouter(tags=["shares"])


def _as_utc(ts: datetime | None) -> datetime | None:
    if ts is None or ts.tzinfo is not None:
        return ts
    return ts.replace(tzinfo=UTC)


@router.get(
    "/presentations/{presentation_id}/share-links",
    response_model=ShareLinkListResponse,
)
@limiter.limit("60/minute")
async def list_share_links(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> ShareLinkListResponse:
    _ = request
    rows = await db.execute(
        select(ShareLink)
        .where(ShareLink.presentation_id == grant.presentation.id)
        .order_by(ShareLink.created_at.desc())
    )
    items = [ShareLinkRead.model_validate(x) for x in rows.scalars().all()]
    return ShareLinkListResponse(items=items)


@router.post(
    "/presentations/{presentation_id}/share-links",
    response_model=ShareLinkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_share_link(
    request: Request,
    body: ShareLinkCreate,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> ShareLinkCreateResponse:
    if grant.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    expires_at = (
        datetime.now(UTC) + timedelta(hours=body.expires_in_hours)
        if body.expires_in_hours is not None
        else None
    )
    row: ShareLink | None = None
    token = ""
    for _attempt in range(3):
        token = secrets.token_urlsafe(24)
        row = ShareLink(
            presentation_id=grant.presentation.id,
            token_hash=hash_share_token(token),
            role=body.role,
            expires_at=expires_at,
            created_by=grant.user.id,
            note=body.note,
        )
        db.add(row)
        try:
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
            row = None
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create share link")

    await db.refresh(row)
    await record_audit(
        db,
        actor_id=grant.user.id,
        action="share_link.created",
        target_kind="share_link",
        target_id=row.id,
        metadata={"presentation_id": str(grant.presentation.id), "role": row.role.value},
        client_ip=client_ip_from_request(request),
    )
    base_url = settings.public_app_url.rstrip("/")
    share_token = quote(token, safe="")
    share_url = f"{base_url}/p/{grant.presentation.id}?share={share_token}"
    base = ShareLinkRead.model_validate(row)
    return ShareLinkCreateResponse(
        **base.model_dump(),
        share_token=token,
        share_url=share_url,
    )


@router.delete(
    "/presentations/{presentation_id}/share-links/{share_link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("30/minute")
async def revoke_share_link(
    request: Request,
    share_link_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> None:
    if grant.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    row = await db.get(ShareLink, share_link_id)
    if row is None or row.presentation_id != grant.presentation.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await db.commit()
        await record_audit(
            db,
            actor_id=grant.user.id,
            action="share_link.revoked",
            target_kind="share_link",
            target_id=row.id,
            metadata={"presentation_id": str(grant.presentation.id)},
            client_ip=client_ip_from_request(request),
        )


@router.post(
    "/share-links/exchange",
    response_model=ShareLinkExchangeResponse,
)
@limiter.limit("120/minute")
async def exchange_share_link(
    request: Request,
    body: ShareLinkExchangeRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShareLinkExchangeResponse:
    _ = request
    token_hash = hash_share_token(body.token.strip())
    result = await db.execute(select(ShareLink).where(ShareLink.token_hash == token_hash))
    link = result.scalar_one_or_none()
    now = datetime.now(UTC)
    link_expires_at = _as_utc(link.expires_at) if link is not None else None
    if (
        link is None
        or link.revoked_at is not None
        or (link_expires_at is not None and link_expires_at < now)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired share link",
        )

    pres = await db.get(Presentation, link.presentation_id)
    if pres is None or pres.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")

    access = create_share_access_token(
        settings,
        share_link_id=link.id,
        presentation_id=link.presentation_id,
        role=link.role.value,
        link_expires_at=link_expires_at,
    )
    cap = now + timedelta(days=7)
    if link_expires_at is not None:
        cap = min(cap, link_expires_at)
    expires_in = max(1, int((cap - now).total_seconds()))
    return ShareLinkExchangeResponse(
        access_token=access,
        expires_in=expires_in,
        presentation_id=link.presentation_id,
        role=link.role,
    )
