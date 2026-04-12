"""Deck LLM credentials: system_settings + env, with optional per-user overrides."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from app.config import Settings
from app.db.models.system_setting import SystemSetting
from app.db.models.user import User
from app.schemas.admin import AdminLlmSettingsRead
from app.services.entra_runtime import load_system_settings_kv
from app.services.token_crypto import decrypt_text, encrypt_text
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

DeckLlmKind = Literal["litellm", "openai", "claude"]

_DECK_LLM_PROVIDER = "deck_llm_provider"
_LITELLM_API_BASE = "litellm_api_base"
_LITELLM_API_KEY_ENC = "litellm_api_key_encrypted"
_OPENAI_API_BASE = "openai_api_base"
_OPENAI_API_KEY_ENC = "openai_api_key_encrypted"
_ANTHROPIC_API_BASE = "anthropic_api_base"
_ANTHROPIC_API_KEY_ENC = "anthropic_api_key_encrypted"

_VALID_PROVIDERS: frozenset[str] = frozenset({"litellm", "openai", "claude"})


class LlmNotConfiguredError(ValueError):
    """Raised when the selected LLM backend is missing required configuration."""


@dataclass(frozen=True, slots=True)
class ResolvedDeckLlm:
    kind: DeckLlmKind
    model: str
    api_base: str | None = None
    api_key: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None


def normalize_deck_llm_provider(raw: str | None) -> DeckLlmKind:
    p = (raw or "litellm").strip().lower()
    if p not in _VALID_PROVIDERS:
        return "litellm"
    return p  # type: ignore[return-value]


def validate_http_api_base(raw: str) -> str:
    base = raw.strip()
    if not base:
        return ""
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("API base URL must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("API base URL must include a host")
    if parsed.username or parsed.password:
        raise ValueError("API base URL must not include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("API base URL must not include query or fragment")
    return base.rstrip("/")


def _effective_system_provider(kv: dict[str, str], settings: Settings) -> DeckLlmKind:
    db_p = (kv.get(_DECK_LLM_PROVIDER) or "").strip()
    env_p = (settings.deck_llm_provider or "").strip()
    return normalize_deck_llm_provider(db_p or env_p or "litellm")


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
    if not api_key and (settings.litellm_api_key or "").strip():
        api_key = (settings.litellm_api_key or "").strip()
    return effective.rstrip("/"), api_key


def _system_openai_key(kv: dict[str, str], settings: Settings) -> str | None:
    enc = (kv.get(_OPENAI_API_KEY_ENC) or "").strip()
    if enc:
        return decrypt_text(settings, enc)
    env_k = (settings.openai_api_key or "").strip()
    return env_k or None


def _system_anthropic_key(kv: dict[str, str], settings: Settings) -> str | None:
    enc = (kv.get(_ANTHROPIC_API_KEY_ENC) or "").strip()
    if enc:
        return decrypt_text(settings, enc)
    env_k = (settings.anthropic_api_key or "").strip()
    return env_k or None


def _system_openai_base(kv: dict[str, str], settings: Settings) -> str | None:
    db_b = (kv.get(_OPENAI_API_BASE) or "").strip() or None
    env_b = (settings.openai_api_base or "").strip() or None
    b = (db_b or env_b or "").strip()
    return b or None


def _system_anthropic_base(kv: dict[str, str], settings: Settings) -> str | None:
    db_b = (kv.get(_ANTHROPIC_API_BASE) or "").strip() or None
    env_b = (settings.anthropic_api_base or "").strip() or None
    b = (db_b or env_b or "").strip()
    return b or None


async def _resolve_system_deck_llm(db: AsyncSession, settings: Settings) -> ResolvedDeckLlm:
    kv = await load_system_settings_kv(db)
    provider = _effective_system_provider(kv, settings)
    model = (settings.deck_llm_model or "").strip() or "gpt-4o-mini"

    if provider == "litellm":
        api_base, api_key = await resolve_litellm_http_credentials(db, settings)
        return ResolvedDeckLlm(kind="litellm", model=model, api_base=api_base, api_key=api_key)

    if provider == "openai":
        key = _system_openai_key(kv, settings)
        if not key:
            raise LlmNotConfiguredError(
                "OpenAI API key is not configured (admin or OPENAI_API_KEY)"
            )
        base = _system_openai_base(kv, settings)
        return ResolvedDeckLlm(
            kind="openai",
            model=model,
            openai_api_key=key,
            openai_base_url=base,
        )

    key = _system_anthropic_key(kv, settings)
    if not key:
        raise LlmNotConfiguredError(
            "Anthropic API key is not configured (admin or ANTHROPIC_API_KEY)"
        )
    base = _system_anthropic_base(kv, settings)
    return ResolvedDeckLlm(
        kind="claude",
        model=model,
        anthropic_api_key=key,
        anthropic_base_url=base,
    )


def _user_openai_key(user: User, settings: Settings) -> str | None:
    enc = (user.llm_openai_key_encrypted or "").strip()
    if enc:
        return decrypt_text(settings, enc)
    legacy = (user.llm_api_key_encrypted or "").strip()
    if legacy and normalize_deck_llm_provider(user.llm_provider) == "openai":
        return decrypt_text(settings, legacy)
    return None


def _user_anthropic_key(user: User, settings: Settings) -> str | None:
    enc = (user.llm_anthropic_key_encrypted or "").strip()
    if enc:
        return decrypt_text(settings, enc)
    legacy = (user.llm_api_key_encrypted or "").strip()
    if legacy and normalize_deck_llm_provider(user.llm_provider) == "claude":
        return decrypt_text(settings, legacy)
    return None


def _user_litellm_key(user: User, settings: Settings) -> str | None:
    enc = (user.llm_litellm_key_encrypted or "").strip()
    if enc:
        return decrypt_text(settings, enc)
    legacy = (user.llm_api_key_encrypted or "").strip()
    if legacy and normalize_deck_llm_provider(user.llm_provider) == "litellm":
        return decrypt_text(settings, legacy)
    return None


def _user_override_resolved(user: User, settings: Settings) -> ResolvedDeckLlm | None:
    prov = normalize_deck_llm_provider(user.llm_provider)
    model = (settings.deck_llm_model or "").strip() or "gpt-4o-mini"

    if user.llm_provider is None or not str(user.llm_provider).strip():
        return None

    if prov == "openai":
        key = _user_openai_key(user, settings)
        if not key:
            return None
        base = (user.llm_openai_base_url or "").strip() or None
        return ResolvedDeckLlm(
            kind="openai",
            model=model,
            openai_api_key=key,
            openai_base_url=base,
        )

    if prov == "claude":
        key = _user_anthropic_key(user, settings)
        if not key:
            return None
        base = (user.llm_anthropic_base_url or "").strip() or None
        return ResolvedDeckLlm(
            kind="claude",
            model=model,
            anthropic_api_key=key,
            anthropic_base_url=base,
        )

    base = (user.llm_litellm_base_url or "").strip()
    if not base:
        return None
    key = _user_litellm_key(user, settings)
    return ResolvedDeckLlm(
        kind="litellm",
        model=model,
        api_base=base.rstrip("/"),
        api_key=key,
    )


async def resolve_deck_llm_credentials(
    db: AsyncSession,
    settings: Settings,
    user_id: uuid.UUID,
) -> ResolvedDeckLlm:
    """Prefer per-user credentials when that user has a full override; else system defaults."""
    user = await db.get(User, user_id)
    if user is not None:
        override = _user_override_resolved(user, settings)
        if override is not None:
            return override
    return await _resolve_system_deck_llm(db, settings)


async def read_litellm_admin_settings(db: AsyncSession, settings: Settings) -> AdminLlmSettingsRead:
    return await read_admin_llm_settings(db, settings)


async def read_admin_llm_settings(db: AsyncSession, settings: Settings) -> AdminLlmSettingsRead:
    kv = await load_system_settings_kv(db)
    provider = _effective_system_provider(kv, settings)

    env_base = (settings.litellm_api_base or "").strip() or None
    db_base = (kv.get(_LITELLM_API_BASE) or "").strip() or None
    litellm_effective = db_base or env_base

    openai_base_db = (kv.get(_OPENAI_API_BASE) or "").strip() or None
    openai_base_env = (settings.openai_api_base or "").strip() or None
    openai_effective = openai_base_db or openai_base_env

    anth_db = (kv.get(_ANTHROPIC_API_BASE) or "").strip() or None
    anth_env = (settings.anthropic_api_base or "").strip() or None
    anth_effective = anth_db or anth_env

    return AdminLlmSettingsRead(
        deck_llm_provider=provider,
        litellm_api_base=litellm_effective,
        litellm_api_base_configured=bool(litellm_effective),
        litellm_api_key_configured=bool(kv.get(_LITELLM_API_KEY_ENC, "").strip())
        or bool((settings.litellm_api_key or "").strip()),
        litellm_api_key_stored_encrypted=True,
        openai_api_base=openai_effective,
        openai_api_base_configured=bool(openai_effective),
        openai_api_key_configured=bool(kv.get(_OPENAI_API_KEY_ENC, "").strip())
        or bool((settings.openai_api_key or "").strip()),
        anthropic_api_base=anth_effective,
        anthropic_api_base_configured=bool(anth_effective),
        anthropic_api_key_configured=bool(kv.get(_ANTHROPIC_API_KEY_ENC, "").strip())
        or bool((settings.anthropic_api_key or "").strip()),
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
    await persist_admin_llm_settings(
        db,
        settings,
        litellm_api_base=api_base,
        litellm_api_key=api_key,
        clear_litellm_api_key=clear_api_key,
        clear_litellm_api_base=clear_api_base,
    )


async def persist_admin_llm_settings(
    db: AsyncSession,
    settings: Settings,
    *,
    deck_llm_provider: str | None = None,
    litellm_api_base: str | None = None,
    litellm_api_key: str | None = None,
    clear_litellm_api_key: bool = False,
    clear_litellm_api_base: bool = False,
    openai_api_base: str | None = None,
    openai_api_key: str | None = None,
    clear_openai_api_key: bool = False,
    clear_openai_api_base: bool = False,
    anthropic_api_base: str | None = None,
    anthropic_api_key: str | None = None,
    clear_anthropic_api_key: bool = False,
    clear_anthropic_api_base: bool = False,
) -> None:
    async def _set(key: str, value: str) -> None:
        row = await db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=value))
        else:
            row.value = value

    changed = False

    if deck_llm_provider is not None:
        p = deck_llm_provider.strip().lower()
        if p not in _VALID_PROVIDERS:
            raise ValueError("deck_llm_provider must be litellm, openai, or claude")
        changed = True
        await _set(_DECK_LLM_PROVIDER, p)

    if clear_litellm_api_base:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_BASE))
    elif litellm_api_base is not None:
        changed = True
        b = validate_http_api_base(litellm_api_base)
        if b:
            await _set(_LITELLM_API_BASE, b)
        else:
            await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_BASE))

    if clear_litellm_api_key:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _LITELLM_API_KEY_ENC))
    elif litellm_api_key is not None and litellm_api_key.strip():
        changed = True
        enc = encrypt_text(settings, litellm_api_key.strip())
        await _set(_LITELLM_API_KEY_ENC, enc)

    if clear_openai_api_base:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _OPENAI_API_BASE))
    elif openai_api_base is not None:
        changed = True
        b = validate_http_api_base(openai_api_base)
        if b:
            await _set(_OPENAI_API_BASE, b)
        else:
            await db.execute(delete(SystemSetting).where(SystemSetting.key == _OPENAI_API_BASE))

    if clear_openai_api_key:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _OPENAI_API_KEY_ENC))
    elif openai_api_key is not None and openai_api_key.strip():
        changed = True
        enc = encrypt_text(settings, openai_api_key.strip())
        await _set(_OPENAI_API_KEY_ENC, enc)

    if clear_anthropic_api_base:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _ANTHROPIC_API_BASE))
    elif anthropic_api_base is not None:
        changed = True
        b = validate_http_api_base(anthropic_api_base)
        if b:
            await _set(_ANTHROPIC_API_BASE, b)
        else:
            await db.execute(delete(SystemSetting).where(SystemSetting.key == _ANTHROPIC_API_BASE))

    if clear_anthropic_api_key:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _ANTHROPIC_API_KEY_ENC))
    elif anthropic_api_key is not None and anthropic_api_key.strip():
        changed = True
        enc = encrypt_text(settings, anthropic_api_key.strip())
        await _set(_ANTHROPIC_API_KEY_ENC, enc)

    if changed:
        await db.commit()
