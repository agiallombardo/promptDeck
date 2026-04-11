from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.security.jwt_tokens import decode_token, decode_token_typed
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
    user: User
    presentation: Presentation
    access: PresentationAccess


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
        uid = uuid.UUID(str(sub))
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
    return result.scalar_one_or_none()


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
    user: User,
    db: AsyncSession,
) -> PresentationGrant:
    row = await _load_presentation_row(db, presentation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    access = await resolve_access(db, row, user)
    if access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return PresentationGrant(user=user, presentation=row, access=access)


async def get_presentation_reader(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, user, db)
    if not can_read(grant.access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_comment_writer(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, user, db)
    if not can_write_comments(grant.access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_editor(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, user, db)
    if not can_manage_presentation(grant.access):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return grant


async def get_presentation_owner(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PresentationGrant:
    grant = await _grant_for_presentation(presentation_id, user, db)
    if not can_delete_presentation(grant.access):
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
