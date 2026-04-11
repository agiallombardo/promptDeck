from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation
from app.db.models.share_link import ShareLink, ShareRole
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.security.jwt_tokens import decode_token
from app.services.acl import (
    PresentationAccess,
    can_delete_presentation,
    can_manage_presentation,
    can_read,
    can_write_comments,
    resolve_access,
)

security = HTTPBearer(auto_error=False)


@dataclass
class PresentationGrant:
    user: User | None
    presentation: Presentation
    access: PresentationAccess


@dataclass
class ShareClaims:
    share_link_id: uuid.UUID
    presentation_id: uuid.UUID
    role: ShareRole


@dataclass
class RequestPrincipal:
    user: User | None = None
    share: ShareClaims | None = None


def _share_access_for_role(role: ShareRole) -> PresentationAccess:
    if role == ShareRole.editor:
        return PresentationAccess.editor
    if role == ShareRole.commenter:
        return PresentationAccess.commenter
    return PresentationAccess.user


def _parse_share_claims(data: dict[str, object]) -> ShareClaims | None:
    sub = data.get("sub")
    presentation_id = data.get("presentation_id")
    role = data.get("role")
    if not sub or not presentation_id or not role:
        return None
    try:
        share_link_id = uuid.UUID(str(sub))
        pres_id = uuid.UUID(str(presentation_id))
        share_role = ShareRole(str(role))
    except (ValueError, TypeError):
        return None
    return ShareClaims(share_link_id=share_link_id, presentation_id=pres_id, role=share_role)


def _as_utc(ts: datetime | None) -> datetime | None:
    if ts is None or ts.tzinfo is not None:
        return ts
    return ts.replace(tzinfo=UTC)


async def get_request_principal_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> RequestPrincipal | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        data = decode_token(settings, creds.credentials)
    except InvalidTokenError:
        return None
    token_type = str(data.get("type") or "")
    if token_type == "access":
        sub = data.get("sub")
        if not sub:
            return None
        try:
            uid = uuid.UUID(str(sub))
        except ValueError:
            return None
        result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
        user = result.scalar_one_or_none()
        return RequestPrincipal(user=user) if user is not None else None
    if token_type == "share_access":
        claims = _parse_share_claims(data)
        if claims is None:
            return None
        return RequestPrincipal(share=claims)
    return None


async def get_request_principal(
    principal: Annotated[RequestPrincipal | None, Depends(get_request_principal_optional)],
) -> RequestPrincipal:
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return principal


async def get_current_user_optional(
    principal: Annotated[RequestPrincipal | None, Depends(get_request_principal_optional)],
) -> User | None:
    if principal is None:
        return None
    return principal.user


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


async def _load_presentation_row(
    db: AsyncSession,
    presentation_id: uuid.UUID,
) -> Presentation | None:
    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _grant_for_presentation(
    presentation_id: uuid.UUID,
    principal: RequestPrincipal,
    db: AsyncSession,
) -> PresentationGrant:
    row = await _load_presentation_row(db, presentation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    if principal.user is not None:
        access = await resolve_access(db, row, principal.user)
        if access is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return PresentationGrant(user=principal.user, presentation=row, access=access)

    if principal.share is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    share = principal.share
    if share.presentation_id != row.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    link = await db.get(ShareLink, share.share_link_id)
    if link is None or link.presentation_id != row.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    now = datetime.now(UTC)
    link_expires_at = _as_utc(link.expires_at)
    if link.revoked_at is not None or (link_expires_at is not None and link_expires_at < now):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return PresentationGrant(user=None, presentation=row, access=_share_access_for_role(share.role))


async def get_presentation_reader(
    presentation_id: uuid.UUID,
    principal: Annotated[RequestPrincipal, Depends(get_request_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, principal, db)
    if not can_read(grant.access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_comment_writer(
    presentation_id: uuid.UUID,
    principal: Annotated[RequestPrincipal, Depends(get_request_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, principal, db)
    if not can_write_comments(grant.access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_editor(
    presentation_id: uuid.UUID,
    principal: Annotated[RequestPrincipal, Depends(get_request_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, principal, db)
    if not can_manage_presentation(grant.access) or grant.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_owner(
    presentation_id: uuid.UUID,
    principal: Annotated[RequestPrincipal, Depends(get_request_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, principal, db)
    if not can_delete_presentation(grant.access) or grant.user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def validate_bearer_token(
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict[str, object]:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_token(settings, creds.credentials)
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
