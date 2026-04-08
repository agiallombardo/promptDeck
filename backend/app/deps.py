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
from app.db.models.share_link import ShareLink
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.security.jwt_tokens import decode_token, decode_token_typed
from app.services.acl import (
    PresentationAccess,
    can_read_presentation,
    can_write_comments,
    effective_access,
)

security = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """Either a signed-in user or a validated share-link session."""

    user: User | None
    share_link: ShareLink | None

    def require_user(self) -> User:
        if self.user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This action requires a signed-in user",
            )
        return self.user

    def asset_identity(self) -> tuple[uuid.UUID, str]:
        """(subject id, role string) for signed asset URLs."""
        if self.user is not None:
            return self.user.id, self.user.role.value
        if self.share_link is not None:
            return self.share_link.id, self.share_link.role.value
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        data = decode_token_typed(settings, creds.credentials, "access")
    except ValueError:
        return None
    sub = data.get("sub")
    if not sub:
        return None
    try:
        uid = uuid.UUID(sub)
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


async def get_principal(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Principal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        data = decode_token(settings, creds.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from e
    typ = data.get("type")
    if typ == "access":
        sub = data.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        try:
            uid = uuid.UUID(sub)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from e
        result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return Principal(user=user, share_link=None)
    if typ == "share_access":
        sub = data.get("sub")
        pres_raw = data.get("presentation_id")
        if not sub or not pres_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid share token",
            )
        try:
            sid = uuid.UUID(sub)
            pres_id = uuid.UUID(str(pres_raw))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid share token",
            ) from e
        link = await db.get(ShareLink, sid)
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Share link not found",
            )
        if link.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Share link revoked")
        if link.presentation_id != pres_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid share token",
            )
        now = datetime.now(UTC)
        if link.expires_at is not None and link.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Share link expired")
        return Principal(user=None, share_link=link)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported token type")


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


async def require_non_viewer(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role == UserRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify comments",
        )
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


async def get_presentation_owner(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Presentation:
    row = await _load_presentation_row(db, presentation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    access = effective_access(row, user=user, share_link=None)
    if access not in (PresentationAccess.admin, PresentationAccess.owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row


async def get_presentation_reader(
    presentation_id: uuid.UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Presentation:
    row = await _load_presentation_row(db, presentation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    if not can_read_presentation(
        row,
        user=principal.user,
        share_link=principal.share_link,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row


async def get_presentation_comment_writer(
    presentation_id: uuid.UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Presentation:
    """Presentation row if the principal may create threads / comments / resolve threads."""
    row = await _load_presentation_row(db, presentation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    if not can_write_comments(row, user=principal.user, share_link=principal.share_link):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row
