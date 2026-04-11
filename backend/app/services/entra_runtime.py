"""Merge env-based Settings with DB-backed system_settings for Entra OIDC."""

from __future__ import annotations

from app.config import Settings
from app.db.models.system_setting import SystemSetting
from app.services.entra import EntraOIDCConfig
from app.services.token_crypto import decrypt_text, encrypt_text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_ENTRA_ENABLED = "entra_enabled"
_ENTRA_TENANT_ID = "entra_tenant_id"
_ENTRA_CLIENT_ID = "entra_client_id"
_ENTRA_CLIENT_SECRET_ENC = "entra_client_secret_encrypted"
_ENTRA_AUTHORITY_HOST = "entra_authority_host"


async def load_system_settings_kv(db: AsyncSession) -> dict[str, str]:
    r = await db.execute(select(SystemSetting))
    return {row.key: row.value for row in r.scalars().all()}


def _strip_or_none(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    return s or None


async def resolve_entra_oidc_config(db: AsyncSession, settings: Settings) -> EntraOIDCConfig:
    base = EntraOIDCConfig.from_settings(settings)
    kv = await load_system_settings_kv(db)

    enabled = base.enabled or kv.get(_ENTRA_ENABLED, "").lower() == "true"

    tenant = _strip_or_none(base.tenant_id) or _strip_or_none(kv.get(_ENTRA_TENANT_ID))
    client_id = _strip_or_none(base.client_id) or _strip_or_none(kv.get(_ENTRA_CLIENT_ID))

    secret = _strip_or_none(base.client_secret)
    if not secret:
        enc = kv.get(_ENTRA_CLIENT_SECRET_ENC)
        if enc and enc.strip():
            try:
                secret = decrypt_text(settings, enc.strip())
            except Exception:  # noqa: BLE001
                secret = None

    authority = _strip_or_none(base.authority_host) or _strip_or_none(kv.get(_ENTRA_AUTHORITY_HOST))
    if not authority:
        authority = base.authority_host

    return EntraOIDCConfig(
        enabled=enabled,
        tenant_id=tenant,
        client_id=client_id,
        client_secret=secret,
        authority_host=authority,
        public_api_url=settings.public_api_url,
    )


def entra_login_ready(cfg: EntraOIDCConfig) -> bool:
    return bool(cfg.enabled and cfg.tenant_id and cfg.client_id and cfg.client_secret)


async def persist_entra_system_settings(
    db: AsyncSession,
    settings: Settings,
    *,
    enabled: bool | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    authority_host: str | None = None,
    clear_client_secret: bool = False,
) -> None:
    async def _set(key: str, value: str) -> None:
        row = await db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value))
        else:
            row.value = value

    changed = False
    if enabled is not None:
        changed = True
        await _set(_ENTRA_ENABLED, "true" if enabled else "false")
    if tenant_id is not None:
        changed = True
        await _set(_ENTRA_TENANT_ID, tenant_id.strip())
    if client_id is not None:
        changed = True
        await _set(_ENTRA_CLIENT_ID, client_id.strip())
    if authority_host is not None:
        changed = True
        await _set(_ENTRA_AUTHORITY_HOST, authority_host.strip())
    if clear_client_secret:
        changed = True
        from sqlalchemy import delete

        await db.execute(delete(SystemSetting).where(SystemSetting.key == _ENTRA_CLIENT_SECRET_ENC))
    elif client_secret is not None and client_secret.strip():
        changed = True
        enc = encrypt_text(settings, client_secret.strip())
        await _set(_ENTRA_CLIENT_SECRET_ENC, enc)
    if changed:
        await db.commit()
