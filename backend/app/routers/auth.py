from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote, urlparse

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
    UserSettingsRead,
    UserSettingsUpdate,
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
from app.services.entra_runtime import entra_login_ready, resolve_entra_oidc_config
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


def _normalized_origin(raw: str | None) -> str | None:
    if raw is None:
        return None
    try:
        parsed = urlparse(raw.strip())
    except ValueError:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".lower()


def _dev_loopback_origin_match(expected_origin: str, actual_origin: str) -> bool:
    """Treat http://127.0.0.1:P and http://localhost:P as the same origin (dev ergonomics)."""
    try:
        e = urlparse(expected_origin)
        a = urlparse(actual_origin)
    except ValueError:
        return False
    eh = (e.hostname or "").lower()
    ah = (a.hostname or "").lower()
    if eh not in ("127.0.0.1", "localhost") or ah not in ("127.0.0.1", "localhost"):
        return False
    if (e.scheme or "").lower() != (a.scheme or "").lower():
        return False
    return e.port == a.port


def _derive_origin_from_request(request: Request) -> str | None:
    """Rebuild browser origin from Host (and forwarded headers) when Origin/Referer are omitted."""
    forwarded = request.headers.get("x-forwarded-host")
    raw_host = (forwarded or request.headers.get("host") or "").strip()
    if not raw_host:
        return None
    host = raw_host.split(",")[0].strip()
    if not host or any(c in host for c in " \n\r/"):
        return None
    xf_proto = request.headers.get("x-forwarded-proto")
    if xf_proto:
        scheme = xf_proto.split(",")[0].strip().lower()
        if scheme not in ("http", "https"):
            scheme = request.url.scheme or "http"
    else:
        scheme = (request.url.scheme or "http").lower()
    return _normalized_origin(f"{scheme}://{host}")


def _assert_same_origin_for_cookie_auth(request: Request, settings: Settings) -> None:
    if settings.environment == "test":
        return
    expected = _normalized_origin(settings.public_app_url)
    if expected is None:
        return
    origin = _normalized_origin(request.headers.get("origin"))
    if origin is None:
        referer = request.headers.get("referer")
        origin = _normalized_origin(referer)
    if origin is None:
        derived = _derive_origin_from_request(request)
        if derived is not None:
            sec_fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
            # Same-origin POST from the SPA often omits Origin/Referer (e.g. Vite proxy + strict
            # referrer policy). Sec-Fetch-Site is still set by modern browsers.
            host_fallback_ok = sec_fetch_site in ("same-origin", "same-site")
            if settings.environment == "development":
                host_fallback_ok = host_fallback_ok or sec_fetch_site == ""
            if host_fallback_ok and (
                derived == expected
                or (
                    settings.environment == "development"
                    and _dev_loopback_origin_match(expected, derived)
                )
            ):
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-site cookie request blocked",
        )
    if origin == expected:
        return
    if settings.environment == "development" and _dev_loopback_origin_match(expected, origin):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cross-site cookie request blocked",
    )


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
async def auth_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthConfigResponse:
    cfg = await resolve_entra_oidc_config(db, settings)
    ready = entra_login_ready(cfg)
    return AuthConfigResponse(
        local_password_auth_enabled=settings.local_password_auth_enabled,
        entra_enabled=ready,
        entra_login_url="/api/v1/auth/entra/login" if ready else None,
    )


@router.get("/entra/login")
async def entra_login(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    next_path: Annotated[str | None, Query(alias="next")] = None,
) -> RedirectResponse:
    try:
        cfg = await resolve_entra_oidc_config(db, settings)
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        login_url = build_authorize_url(cfg, state=state, nonce=nonce)
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
        cfg = await resolve_entra_oidc_config(db, settings)
        tokens = await exchange_code_for_tokens(cfg, code)
        id_token = str(tokens.get("id_token") or "")
        if not id_token:
            raise EntraAuthError("Missing Microsoft Entra ID token")
        claims = parse_id_token(cfg, id_token, nonce)
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
    await db.commit()
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
        await db.commit()
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
    await db.commit()
    return out


@router.get("/me", response_model=UserPublic)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)


@router.get("/me/settings", response_model=UserSettingsRead)
async def me_settings(user: Annotated[User, Depends(get_current_user)]) -> UserSettingsRead:
    from app.services.llm_runtime import normalize_deck_llm_provider

    any_key = bool(
        user.llm_api_key_encrypted
        or user.llm_openai_key_encrypted
        or user.llm_anthropic_key_encrypted
        or user.llm_litellm_key_encrypted
    )
    return UserSettingsRead(
        llm_provider=user.llm_provider,
        openai_api_base=user.llm_openai_base_url,
        anthropic_api_base=user.llm_anthropic_base_url,
        litellm_api_base=user.llm_litellm_base_url,
        openai_api_key_configured=bool(user.llm_openai_key_encrypted)
        or (
            bool(user.llm_api_key_encrypted)
            and normalize_deck_llm_provider(user.llm_provider) == "openai"
        ),
        anthropic_api_key_configured=bool(user.llm_anthropic_key_encrypted)
        or (
            bool(user.llm_api_key_encrypted)
            and normalize_deck_llm_provider(user.llm_provider) == "claude"
        ),
        litellm_api_key_configured=bool(user.llm_litellm_key_encrypted)
        or (
            bool(user.llm_api_key_encrypted)
            and normalize_deck_llm_provider(user.llm_provider) == "litellm"
        ),
        llm_api_key_configured=any_key,
    )


@router.patch("/me/settings", response_model=UserSettingsRead)
async def me_settings_patch(
    body: UserSettingsUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserSettingsRead:
    from app.services.llm_runtime import validate_http_api_base

    if body.clear_llm_provider:
        user.llm_provider = None
    elif body.llm_provider is not None:
        user.llm_provider = body.llm_provider

    def _apply_base(raw: str | None, *, clear: bool, attr: str) -> None:
        if clear:
            setattr(user, attr, None)
            return
        if raw is None:
            return
        try:
            b = validate_http_api_base(raw)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        setattr(user, attr, b or None)

    _apply_base(body.openai_api_base, clear=body.clear_openai_api_base, attr="llm_openai_base_url")
    _apply_base(
        body.anthropic_api_base,
        clear=body.clear_anthropic_api_base,
        attr="llm_anthropic_base_url",
    )
    _apply_base(
        body.litellm_api_base,
        clear=body.clear_litellm_api_base,
        attr="llm_litellm_base_url",
    )

    if body.clear_openai_api_key:
        user.llm_openai_key_encrypted = None
    elif body.openai_api_key is not None and body.openai_api_key.strip():
        user.llm_openai_key_encrypted = encrypt_text(settings, body.openai_api_key.strip())

    if body.clear_anthropic_api_key:
        user.llm_anthropic_key_encrypted = None
    elif body.anthropic_api_key is not None and body.anthropic_api_key.strip():
        user.llm_anthropic_key_encrypted = encrypt_text(settings, body.anthropic_api_key.strip())

    if body.clear_litellm_api_key:
        user.llm_litellm_key_encrypted = None
    elif body.litellm_api_key is not None and body.litellm_api_key.strip():
        user.llm_litellm_key_encrypted = encrypt_text(settings, body.litellm_api_key.strip())

    if body.clear_llm_api_key:
        user.llm_api_key_encrypted = None
    elif body.llm_api_key is not None and body.llm_api_key.strip():
        user.llm_api_key_encrypted = encrypt_text(settings, body.llm_api_key.strip())

    await db.commit()
    await db.refresh(user)
    return await me_settings(user)


@router.post("/refresh", response_model=LoginResponse)
@limiter.limit("60/minute")
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    _assert_same_origin_for_cookie_auth(request, settings)
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
        await db.commit()
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
        await db.commit()
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
        await db.commit()
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
    await db.commit()
    return out


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("60/minute")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    _assert_same_origin_for_cookie_auth(request, settings)
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
    await db.commit()
    return MessageResponse(message="Logged out")
