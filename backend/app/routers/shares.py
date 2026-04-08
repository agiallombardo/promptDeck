from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation
from app.db.models.share_link import ShareLink
from app.db.models.user import User
from app.db.session import get_db
from app.deps import get_current_user, get_presentation_owner
from app.schemas.share import (
    ShareCreate,
    ShareCreated,
    ShareExchangeRequest,
    ShareExchangeResponse,
    ShareListResponse,
    ShareRead,
)
from app.security.jwt_tokens import create_share_access_token, decode_token
from app.services.share_tokens import hash_share_token

router = APIRouter(tags=["shares"])


@router.post(
    "/presentations/{presentation_id}/shares",
    response_model=ShareCreated,
    status_code=201,
)
async def create_share_link(
    body: ShareCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> ShareCreated:
    plaintext = secrets.token_urlsafe(32)
    link = ShareLink(
        presentation_id=presentation.id,
        token_hash=hash_share_token(plaintext),
        role=body.role,
        expires_at=body.expires_at,
        created_by=user.id,
        note=body.note,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    data = ShareRead.model_validate(link).model_dump()
    data["token"] = plaintext
    return ShareCreated.model_validate(data)


@router.get("/presentations/{presentation_id}/shares", response_model=ShareListResponse)
async def list_share_links(
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> ShareListResponse:
    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.presentation_id == presentation.id)
        .order_by(ShareLink.created_at.desc())
    )
    rows = result.scalars().all()
    return ShareListResponse(items=[ShareRead.model_validate(x) for x in rows])


@router.delete(
    "/presentations/{presentation_id}/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_share_link(
    share_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> None:
    link = await db.get(ShareLink, share_id)
    if link is None or link.presentation_id != presentation.id:
        raise HTTPException(status_code=404, detail="Share link not found")
    link.revoked_at = datetime.now(UTC)
    await db.commit()


@router.post("/shares/exchange", response_model=ShareExchangeResponse)
async def exchange_share_token(
    body: ShareExchangeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ShareExchangeResponse:
    h = hash_share_token(body.token.strip())
    result = await db.execute(select(ShareLink).where(ShareLink.token_hash == h))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if link.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Share link revoked")
    now = datetime.now(UTC)
    if link.expires_at is not None and link.expires_at <= now:
        raise HTTPException(status_code=403, detail="Share link expired")

    access = create_share_access_token(
        settings,
        share_link_id=link.id,
        presentation_id=link.presentation_id,
        role=link.role.value,
        link_expires_at=link.expires_at,
    )
    data = decode_token(settings, access)
    exp = int(data["exp"])
    expires_in = max(0, exp - int(now.timestamp()))
    return ShareExchangeResponse(
        access_token=access,
        expires_in=expires_in,
        presentation_id=link.presentation_id,
        role=link.role,
    )
