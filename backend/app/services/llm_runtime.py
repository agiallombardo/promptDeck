"""System-wide LiteLLM / OpenAI-compatible API base + key in system_settings (with env fallback)."""

from __future__ import annotations

from urllib.parse import urlparse

from app.config import Settings
from app.db.models.system_setting import SystemSetting
from app.schemas.admin import AdminLlmSettingsRead
from app.services.entra_runtime import load_system_settings_kv
from app.services.token_crypto import decrypt_text, encrypt_text
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

_LITELLM_API_BASE = "litellm_api_base"
_LITELLM_API_KEY_ENC = "litellm_api_key_encrypted"


class LlmNotConfiguredError(ValueError):
    """Raised when LiteLLM base URL is missing (env + DB)."""


async def resolve_litellm_http_credentials(
    db: AsyncSession,
    settings: Settings,
) -> tuple[str, str | None]:
    """Return (api_base_url, api_key_or_none) for OpenAI-compatible chat/completions."""
    kv = await load_system_settings_kv(db)
    env_base = (settings.litellm_api_base or "").strip() or None
    db_base = (kv.get(_LITELLM_API_BASE) or "").strip() or None
    effective = (db_base or env_base or "").strip()
    if not effective:
        raise LlmNotConfiguredError("LiteLLM / OpenAI-compatible API base is not configured")
    key_enc = (kv.get(_LITELLM_API_KEY_ENC) or "").strip()
    api_key: str | None = decrypt_text(settings, key_enc) if key_enc else None
    return effective.rstrip("/"), api_key


def _validate_litellm_api_base(raw: str) -> str:
    base = raw.strip()
    if not base:
        return ""
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("LiteLLM API base must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("LiteLLM API base must include a host")
    if parsed.username or parsed.password:
        raise ValueError("LiteLLM API base must not include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("LiteLLM API base must not include query or fragment")
    return base.rstrip("/")


async def read_litellm_admin_settings(db: AsyncSession, settings: Settings) -> AdminLlmSettingsRead:
    kv = await load_system_settings_kv(db)
    env_base = (settings.litellm_api_base or "").strip() or None
    db_base = (kv.get(_LITELLM_API_BASE) or "").strip() or None
    effective = db_base or env_base
    key_ok = bool(kv.get(_LITELLM_API_KEY_ENC, "").strip())
    return AdminLlmSettingsRead(
        litellm_api_base=effective,
        litellm_api_base_configured=bool(effective),
        litellm_api_key_configured=key_ok,
    )


async def persist_litellm_system_settings(
    db: AsyncSession,
    settings: Settings,
    *,
    api_base: str | None = None,
    api_key: str | None = None,
    clear_api_key: bool = False,
    clear_api_base: bool = False,
) -> None:
    async def _set(key: str, value: str) -> None:
        row = await db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value))
        else:
            row.value = value

    changed = False
    if clear_api_base:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_BASE))
    elif api_base is not None:
        changed = True
        b = _validate_litellm_api_base(api_base)
        if b:
            await _set(_LITELLM_API_BASE, b)
        else:
            await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_BASE))

    if clear_api_key:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_KEY_ENC))
    elif api_key is not None and api_key.strip():
        changed = True
        enc = encrypt_text(settings, api_key.strip())
        await _set(_LITELLM_API_KEY_ENC, enc)

    if changed:
        await db.commit()
