from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.security.jwt_tokens import decode_token_typed

security = HTTPBearer(auto_error=False)


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


async def get_presentation(
    presentation_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Presentation:
    result = await db.execute(
        select(Presentation).where(
            Presentation.id == presentation_id,
            Presentation.deleted_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    if user.role != UserRole.admin and row.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return row
