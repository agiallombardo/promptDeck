from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.user import AuthProvider, User
from app.db.session import get_db
from app.deps import get_current_user
from app.rate_limit import limiter
from app.schemas.directory import DirectoryUserListResponse, DirectoryUserRead
from app.services.entra import (
    EntraAuthError,
    exchange_refresh_token_for_graph_token,
    search_directory_users,
)
from app.services.entra_runtime import resolve_entra_oidc_config
from app.services.token_crypto import decrypt_text

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/users", response_model=DirectoryUserListResponse)
@limiter.limit("120/minute")
async def directory_users(
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DirectoryUserListResponse:
    _ = request
    if user.auth_provider != AuthProvider.entra or not user.entra_refresh_token_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Directory search requires Microsoft Entra sign-in",
        )
    try:
        cfg = await resolve_entra_oidc_config(db, settings)
        refresh_token = decrypt_text(settings, user.entra_refresh_token_encrypted)
        graph_access_token = await exchange_refresh_token_for_graph_token(cfg, refresh_token)
        rows = await search_directory_users(cfg, graph_access_token, q.strip())
    except EntraAuthError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return DirectoryUserListResponse(items=[DirectoryUserRead.model_validate(x) for x in rows])
