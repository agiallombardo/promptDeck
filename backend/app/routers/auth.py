from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.user import User
from app.db.session import get_db
from app.deps import get_current_user
from app.logging_channels import LogChannel, channel_logger
from app.rate_limit import limiter
from app.schemas.auth import LoginRequest, LoginResponse, MessageResponse, UserPublic
from app.security.jwt_tokens import create_access_token, create_refresh_token, decode_token_typed
from app.security.passwords import verify_password
from app.services.app_logging import write_app_log
from app.services.audit import client_ip_from_request, record_audit

router = APIRouter()
log = channel_logger(LogChannel.auth)
REFRESH_COOKIE = "refresh_token"


async def _persist_auth_log(
    db: AsyncSession,
    *,
    request: Request,
    level: str,
    event: str,
    user_id: uuid.UUID | None,
    status_code: int,
    payload: dict | None = None,
) -> None:
    await write_app_log(
        db,
        channel=LogChannel.auth,
        level=level,
        event=event,
        request_id=getattr(request.state, "request_id", None),
        user_id=user_id,
        path=str(request.url.path),
        method=request.method,
        status_code=status_code,
        latency_ms=None,
        payload=payload,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    email = body.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        log.warning("auth.login.failure", email=email)
        await _persist_auth_log(
            db,
            request=request,
            level="warning",
            event="auth.login.failure",
            user_id=None,
            status_code=401,
            payload={"email": email},
        )
        await record_audit(
            db,
            actor_id=None,
            action="auth.login.failure",
            metadata={"email": email},
            client_ip=client_ip_from_request(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)

    access = create_access_token(
        settings,
        user_id=user.id,
        email=user.email,
        role=str(user.role),
    )
    refresh = create_refresh_token(settings, user_id=user.id)

    max_age = settings.refresh_token_expire_days * 24 * 3600
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/api/v1",
    )
    log.info("auth.login.success", user_id=str(user.id), email=user.email)
    await _persist_auth_log(
        db,
        request=request,
        level="info",
        event="auth.login.success",
        user_id=user.id,
        status_code=200,
        payload={"email": user.email},
    )
    await record_audit(
        db,
        actor_id=user.id,
        action="auth.login.success",
        metadata={"email": user.email},
        client_ip=client_ip_from_request(request),
    )
    return LoginResponse(
        access_token=access,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.post("/refresh", response_model=LoginResponse)
@limiter.limit("60/minute")
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        log.warning("auth.refresh.missing_cookie")
        await _persist_auth_log(
            db,
            request=request,
            level="warning",
            event="auth.refresh.missing_cookie",
            user_id=None,
            status_code=401,
            payload=None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    try:
        data = decode_token_typed(settings, token, "refresh")
    except ValueError as e:
        response.delete_cookie(REFRESH_COOKIE, path="/api/v1")
        log.warning("auth.refresh.invalid_token")
        await _persist_auth_log(
            db,
            request=request,
            level="warning",
            event="auth.refresh.invalid_token",
            user_id=None,
            status_code=401,
            payload=None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from e

    uid = uuid.UUID(str(data["sub"]))
    result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None:
        response.delete_cookie(REFRESH_COOKIE, path="/api/v1")
        log.warning("auth.refresh.user_missing", sub=str(uid))
        await _persist_auth_log(
            db,
            request=request,
            level="warning",
            event="auth.refresh.user_not_found",
            user_id=None,
            status_code=401,
            payload={"sub": str(uid)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access = create_access_token(
        settings,
        user_id=user.id,
        email=user.email,
        role=str(user.role),
    )
    new_refresh = create_refresh_token(settings, user_id=user.id)
    max_age = settings.refresh_token_expire_days * 24 * 3600
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=new_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/api/v1",
    )
    log.info("auth.refresh.success", user_id=str(user.id))
    await _persist_auth_log(
        db,
        request=request,
        level="info",
        event="auth.refresh.success",
        user_id=user.id,
        status_code=200,
        payload=None,
    )
    return LoginResponse(
        access_token=access,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    log.info("auth.logout")
    await _persist_auth_log(
        db,
        request=request,
        level="info",
        event="auth.logout",
        user_id=None,
        status_code=200,
        payload=None,
    )
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1")
    return MessageResponse(message="ok")


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)
