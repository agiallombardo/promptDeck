from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from app.config import Settings
from jwt import PyJWKClient

OIDC_SCOPES = ["openid", "profile", "email", "offline_access", "User.ReadBasic.All"]
GRAPH_SCOPES = ["https://graph.microsoft.com/User.ReadBasic.All"]


@dataclass(slots=True)
class EntraUserInfo:
    tenant_id: str
    object_id: str
    email: str
    display_name: str | None
    user_type: str | None


class EntraConfigError(RuntimeError):
    pass


class EntraAuthError(RuntimeError):
    pass


async def exchange_code_for_tokens(settings: Settings, code: str) -> dict[str, Any]:
    return await _token_request(
        settings,
        {
            "client_id": settings.entra_client_id or "",
            "client_secret": settings.entra_client_secret or "",
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.entra_redirect_uri,
            "scope": " ".join(OIDC_SCOPES),
        },
    )


async def exchange_refresh_token_for_graph_token(settings: Settings, refresh_token: str) -> str:
    payload = await _token_request(
        settings,
        {
            "client_id": settings.entra_client_id or "",
            "client_secret": settings.entra_client_secret or "",
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(GRAPH_SCOPES),
        },
    )
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise EntraAuthError("Missing Graph access token")
    return access_token


async def search_directory_users(
    settings: Settings,
    access_token: str,
    query: str,
) -> list[dict[str, Any]]:
    q = _escape_odata_value(query)
    params = {
        "$select": "id,displayName,mail,userPrincipalName,userType",
        "$top": "10",
        "$filter": (
            f"startswith(displayName,'{q}') or startswith(mail,'{q}') or "
            f"startswith(userPrincipalName,'{q}')"
        ),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/users",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise EntraAuthError("Microsoft Graph directory search failed")
    payload = response.json()
    value = payload.get("value")
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        object_id = str(row.get("id") or "").strip()
        email = str(row.get("mail") or row.get("userPrincipalName") or "").strip().lower()
        if not object_id or not email:
            continue
        out.append(
            {
                "entra_object_id": object_id,
                "email": email,
                "display_name": _clean_optional(row.get("displayName")),
                "user_type": _clean_optional(row.get("userType")),
            }
        )
    return out


async def _token_request(settings: Settings, data: dict[str, str]) -> dict[str, Any]:
    _validate_config(settings)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{settings.entra_authority}/token", data=data)
    if response.status_code >= 400:
        raise EntraAuthError("Microsoft Entra token exchange failed")
    payload = response.json()
    if not isinstance(payload, dict):
        raise EntraAuthError("Invalid Microsoft Entra token response")
    return payload


@lru_cache
def _jwk_client(authority: str) -> PyJWKClient:
    return PyJWKClient(f"{authority}/discovery/v2.0/keys")


def parse_id_token(settings: Settings, id_token: str, nonce: str) -> EntraUserInfo:
    _validate_config(settings)
    signing_key = _jwk_client(settings.entra_authority).get_signing_key_from_jwt(id_token)
    issuer = f"{settings.entra_authority_host.rstrip('/')}/{settings.entra_tenant_id}/v2.0"
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.entra_client_id,
        issuer=issuer,
    )
    token_nonce = str(claims.get("nonce") or "")
    if token_nonce != nonce:
        raise EntraAuthError("Invalid Microsoft Entra nonce")

    tenant_id = str(claims.get("tid") or "").strip()
    object_id = str(claims.get("oid") or "").strip()
    email = (
        str(claims.get("email") or claims.get("preferred_username") or claims.get("upn") or "")
        .strip()
        .lower()
    )
    if not tenant_id or not object_id or not email:
        raise EntraAuthError("Incomplete Microsoft Entra identity claims")
    if tenant_id != settings.entra_tenant_id:
        raise EntraAuthError("Unexpected Microsoft Entra tenant")
    return EntraUserInfo(
        tenant_id=tenant_id,
        object_id=object_id,
        email=email,
        display_name=_clean_optional(claims.get("name")),
        user_type=_clean_optional(claims.get("user_type")),
    )


def build_authorize_url(settings: Settings, *, state: str, nonce: str) -> str:
    _validate_config(settings)
    query = urlencode(
        {
            "client_id": settings.entra_client_id,
            "response_type": "code",
            "redirect_uri": settings.entra_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(OIDC_SCOPES),
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
    )
    return f"{settings.entra_authority}/authorize?{query}"


def _validate_config(settings: Settings) -> None:
    if not settings.entra_enabled:
        raise EntraConfigError("Microsoft Entra authentication is disabled")
    required = [settings.entra_tenant_id, settings.entra_client_id, settings.entra_client_secret]
    if not all(required):
        raise EntraConfigError("Microsoft Entra configuration is incomplete")


def _escape_odata_value(value: str) -> str:
    return value.replace("'", "''")


def _clean_optional(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
