from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.config import Settings, get_settings
from app.db.models.presentation_member import PresentationMember
from app.db.models.user import AuthProvider, User, UserRole
from app.db.session import get_db
from app.deps import get_current_user
from app.logging_channels import LogChannel, channel_logger
from app.rate_limit import limiter
from app.schemas.auth import (
    AuthConfigResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    UserPublic,
)
from app.security.jwt_tokens import create_access_token, create_refresh_token, decode_token_typed
from app.security.passwords import verify_password
from app.services.app_logging import write_app_log
from app.services.audit import client_ip_from_request, record_audit
from app.services.entra import (
    EntraAuthError,
    EntraConfigError,
    build_authorize_url,
    exchange_code_for_tokens,
    parse_id_token,
)
from app.services.token_crypto import encrypt_text

router = APIRouter()
log = channel_logger(LogChannel.auth)
REFRESH_COOKIE = "refresh_token"
STATE_COOKIE = "entra_auth_state"
NONCE_COOKIE = "entra_auth_nonce"
NEXT_COOKIE = "entra_auth_next"


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


def _set_refresh_cookie(response: Response, settings: Settings, refresh_token: str) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 3600
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=max_age,
        path="/api/v1",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1")


def _clear_entra_cookies(response: Response) -> None:
    for key in (STATE_COOKIE, NONCE_COOKIE, NEXT_COOKIE):
        response.delete_cookie(key, path="/api/v1/auth/entra")


def _login_response(settings: Settings, user: User, response: Response) -> LoginResponse:
    access = create_access_token(
        settings,
        user_id=user.id,
        email=user.email,
        role=str(user.role),
    )
    refresh = create_refresh_token(settings, user_id=user.id)
    _set_refresh_cookie(response, settings, refresh)
    return LoginResponse(
        access_token=access,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.model_validate(user),
    )


def _safe_next_path(raw: str | None) -> str:
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return "/files"


async def _upsert_entra_user(
    db: AsyncSession,
    settings: Settings,
    *,
    tenant_id: str,
    object_id: str,
    email: str,
    display_name: str | None,
    user_type: str | None,
    refresh_token: str | None,
) -> User:
    result = await db.execute(
        select(User).where(
            User.entra_tenant_id == tenant_id,
            User.entra_object_id == object_id,
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user is None:
        result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

    encrypted_refresh = encrypt_text(settings, refresh_token) if refresh_token else None
    if user is None:
        user = User(
            email=email,
            display_name=display_name,
            role=UserRole.user,
            auth_provider=AuthProvider.entra,
            entra_tenant_id=tenant_id,
            entra_object_id=object_id,
            entra_user_type=user_type,
            entra_refresh_token_encrypted=encrypted_refresh,
        )
        db.add(user)
        await db.flush()
    else:
        user.email = email
        user.display_name = display_name
        user.auth_provider = AuthProvider.entra
        user.entra_tenant_id = tenant_id
        user.entra_object_id = object_id
        user.entra_user_type = user_type
        if encrypted_refresh:
            user.entra_refresh_token_encrypted = encrypted_refresh

    user.last_login_at = datetime.now(UTC)
    await db.flush()

    result2 = await db.execute(
        select(PresentationMember).where(
            PresentationMember.principal_tenant_id == tenant_id,
            PresentationMember.principal_entra_object_id == object_id,
            PresentationMember.revoked_at.is_(None),
        )
    )
    for member in result2.scalars().all():
        member.user_id = user.id
        member.principal_email = email
        member.principal_display_name = display_name
        member.principal_user_type = user_type

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/config", response_model=AuthConfigResponse)
async def auth_config(settings: Annotated[Settings, Depends(get_settings)]) -> AuthConfigResponse:
    return AuthConfigResponse(
        local_password_auth_enabled=settings.local_password_auth_enabled,
        entra_enabled=settings.entra_enabled,
        entra_login_url="/api/v1/auth/entra/login" if settings.entra_enabled else None,
    )


@router.get("/entra/login")
async def entra_login(
    settings: Annotated[Settings, Depends(get_settings)],
    next_path: Annotated[str | None, Query(alias="next")] = None,
) -> RedirectResponse:
    try:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        login_url = build_authorize_url(settings, state=state, nonce=nonce)
    except EntraConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    response = RedirectResponse(login_url, status_code=status.HTTP_302_FOUND)
    cookie_kwargs = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "max_age": 600,
        "path": "/api/v1/auth/entra",
    }
    response.set_cookie(STATE_COOKIE, state, **cookie_kwargs)
    response.set_cookie(NONCE_COOKIE, nonce, **cookie_kwargs)
    response.set_cookie(NEXT_COOKIE, _safe_next_path(next_path), **cookie_kwargs)
    return response


@router.get("/entra/callback")
async def entra_callback(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        redirect = RedirectResponse(
            f"{settings.public_app_url.rstrip('/')}/login?error={quote(error)}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_entra_cookies(redirect)
        return redirect

    expected_state = request.cookies.get(STATE_COOKIE)
    nonce = request.cookies.get(NONCE_COOKIE)
    next_path = _safe_next_path(request.cookies.get(NEXT_COOKIE))
    if not code or not state or not expected_state or state != expected_state or not nonce:
        redirect = RedirectResponse(
            f"{settings.public_app_url.rstrip('/')}/login?error={quote('Authentication failed')}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_entra_cookies(redirect)
        return redirect

    try:
        tokens = await exchange_code_for_tokens(settings, code)
        id_token = str(tokens.get("id_token") or "")
        if not id_token:
            raise EntraAuthError("Missing Microsoft Entra ID token")
        claims = parse_id_token(settings, id_token, nonce)
        refresh_token = (
            tokens.get("refresh_token") if isinstance(tokens.get("refresh_token"), str) else None
        )
        user = await _upsert_entra_user(
            db,
            settings,
            tenant_id=claims.tenant_id,
            object_id=claims.object_id,
            email=claims.email,
            display_name=claims.display_name,
            user_type=claims.user_type,
            refresh_token=refresh_token,
        )
    except (EntraAuthError, EntraConfigError) as e:
        redirect = RedirectResponse(
            f"{settings.public_app_url.rstrip('/')}/login?error={quote(str(e))}",
            status_code=status.HTTP_302_FOUND,
        )
        _clear_entra_cookies(redirect)
        return redirect

    session_response = RedirectResponse(
        f"{settings.public_app_url.rstrip('/')}{next_path}",
        status_code=status.HTTP_302_FOUND,
    )
    refresh = create_refresh_token(settings, user_id=user.id)
    _set_refresh_cookie(session_response, settings, refresh)
    _clear_entra_cookies(session_response)
    log.info("auth.entra.login.success", user_id=str(user.id), email=user.email)
    await _persist_auth_log(
        db,
        request=request,
        level="info",
        event="auth.entra.login.success",
        user_id=user.id,
        status_code=302,
        payload={"email": user.email},
    )
    await record_audit(
        db,
        actor_id=user.id,
        action="auth.entra.login.success",
        metadata={"email": user.email},
        client_ip=client_ip_from_request(request),
    )
    return session_response


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    if not settings.local_password_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local login disabled")

    email = body.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
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

    out = _login_response(settings, user, response)
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
    return out


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)


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
        _clear_refresh_cookie(response)
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
        _clear_refresh_cookie(response)
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

    out = _login_response(settings, user, response)
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
    return out


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    _clear_refresh_cookie(response)
    _clear_entra_cookies(response)
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
    return MessageResponse(message="Logged out")
