"""Merge env Settings with DB system_settings for outbound SMTP (e.g. Microsoft 365 relay)."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Literal

import aiosmtplib
import structlog
from app.config import Settings
from app.db.models.system_setting import SystemSetting
from app.schemas.admin import AdminSmtpSettingsPatch
from app.services.entra_runtime import load_system_settings_kv
from app.services.token_crypto import decrypt_text, encrypt_text
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

_SMTP_ENABLED = "smtp_enabled"
_SMTP_HOST = "smtp_host"
_SMTP_PORT = "smtp_port"
_SMTP_USERNAME = "smtp_username"
_SMTP_PASSWORD_ENC = "smtp_password_encrypted"
_SMTP_FROM = "smtp_from"
_SMTP_STARTTLS = "smtp_starttls"
_SMTP_IMPLICIT_TLS = "smtp_implicit_tls"
_SMTP_VALIDATE_CERTS = "smtp_validate_certs"
_SMTP_AUTH_MODE = "smtp_auth_mode"

SmtpAuthMode = Literal["login", "none"]


@dataclass(slots=True)
class SmtpConfig:
    enabled: bool
    host: str | None
    port: int
    username: str | None
    password: str | None
    from_address: str | None
    starttls: bool
    implicit_tls: bool
    validate_certs: bool
    auth_mode: SmtpAuthMode


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _normalize_auth_mode(raw: str | None, default: SmtpAuthMode) -> SmtpAuthMode:
    if raw is None or not raw.strip():
        return default
    s = raw.strip().lower()
    if s in ("none", "relay", "anonymous"):
        return "none"
    return "login"


def _password_from_kv(settings: Settings, kv: dict[str, str]) -> str | None:
    enc = kv.get(_SMTP_PASSWORD_ENC)
    if enc and enc.strip():
        with contextlib.suppress(Exception):
            return decrypt_text(settings, enc.strip())
    return None


async def resolve_smtp_config(db: AsyncSession, settings: Settings) -> SmtpConfig:
    kv = await load_system_settings_kv(db)

    if _SMTP_ENABLED in kv:
        enabled = _parse_bool(kv.get(_SMTP_ENABLED), False)
    else:
        enabled = settings.smtp_enabled

    host = (kv.get(_SMTP_HOST) or "").strip() or (settings.smtp_host or "").strip() or None

    if _SMTP_PORT in kv and kv[_SMTP_PORT].strip().isdigit():
        port = int(kv[_SMTP_PORT].strip())
    else:
        port = settings.smtp_port

    username = (kv.get(_SMTP_USERNAME) or "").strip() or (settings.smtp_user or "").strip() or None
    from_address = (kv.get(_SMTP_FROM) or "").strip() or (settings.smtp_from or "").strip() or None

    if _SMTP_STARTTLS in kv:
        starttls = _parse_bool(kv.get(_SMTP_STARTTLS), True)
    else:
        starttls = settings.smtp_starttls

    if _SMTP_IMPLICIT_TLS in kv:
        implicit_tls = _parse_bool(kv.get(_SMTP_IMPLICIT_TLS), False)
    else:
        implicit_tls = settings.smtp_implicit_tls

    if _SMTP_VALIDATE_CERTS in kv:
        validate_certs = _parse_bool(kv.get(_SMTP_VALIDATE_CERTS), True)
    else:
        validate_certs = settings.smtp_validate_certs

    if _SMTP_AUTH_MODE in kv:
        auth_mode = _normalize_auth_mode(kv.get(_SMTP_AUTH_MODE), "login")
    else:
        auth_mode = settings.smtp_auth_mode

    password = _password_from_kv(settings, kv) or (settings.smtp_password or "").strip() or None

    return SmtpConfig(
        enabled=enabled,
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        starttls=starttls,
        implicit_tls=implicit_tls,
        validate_certs=validate_certs,
        auth_mode=auth_mode,
    )


def smtp_uses_encrypted_transport(cfg: SmtpConfig) -> bool:
    """Exactly one of STARTTLS or implicit TLS (mutually exclusive)."""
    return bool(cfg.starttls) ^ bool(cfg.implicit_tls)


def smtp_password_configured(settings: Settings, kv: dict[str, str]) -> bool:
    if settings.smtp_password and settings.smtp_password.strip():
        return True
    enc = kv.get(_SMTP_PASSWORD_ENC, "")
    return bool(enc and enc.strip())


def assert_smtp_config_valid(cfg: SmtpConfig) -> None:
    """Raise ValueError if enabled SMTP settings are inconsistent or insecure."""
    if not cfg.enabled:
        return
    if not (cfg.host and cfg.from_address and cfg.port):
        return
    if not smtp_uses_encrypted_transport(cfg):
        raise ValueError(
            "When SMTP is enabled, use exactly one of: STARTTLS (e.g. port 587) or "
            "implicit TLS / SSL (e.g. port 465). Unencrypted SMTP is not supported."
        )
    if cfg.auth_mode == "login":
        if not (cfg.username and cfg.username.strip()):
            raise ValueError("Login authentication requires an SMTP username.")
        if not (cfg.password and cfg.password.strip()):
            raise ValueError("Login authentication requires an SMTP password (stored encrypted).")


def smtp_ready(cfg: SmtpConfig) -> bool:
    if not cfg.enabled or not cfg.host or not cfg.from_address or not cfg.port:
        return False
    if not smtp_uses_encrypted_transport(cfg):
        return False
    if cfg.starttls and cfg.implicit_tls:
        return False
    if cfg.auth_mode == "login":
        return bool(cfg.username and cfg.password)
    return cfg.auth_mode == "none"


def _opt_str(v: object | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def merge_smtp_settings_patch(cfg: SmtpConfig, patch: AdminSmtpSettingsPatch) -> SmtpConfig:
    d = patch.model_dump(exclude_unset=True)
    enabled = bool(d["smtp_enabled"]) if "smtp_enabled" in d else cfg.enabled

    if "smtp_host" in d:
        host = _opt_str(d["smtp_host"]) if d["smtp_host"] is not None else None
    else:
        host = cfg.host

    port = int(d["smtp_port"]) if "smtp_port" in d and d["smtp_port"] is not None else cfg.port

    if "smtp_username" in d:
        username = _opt_str(d["smtp_username"]) if d["smtp_username"] is not None else None
    else:
        username = cfg.username

    if "smtp_from" in d:
        from_address = _opt_str(d["smtp_from"]) if d["smtp_from"] is not None else None
    else:
        from_address = cfg.from_address

    starttls = bool(d["smtp_starttls"]) if "smtp_starttls" in d else cfg.starttls
    implicit_tls = bool(d["smtp_implicit_tls"]) if "smtp_implicit_tls" in d else cfg.implicit_tls
    if "smtp_validate_certs" in d:
        validate_certs = bool(d["smtp_validate_certs"])
    else:
        validate_certs = cfg.validate_certs

    auth_mode: SmtpAuthMode = cfg.auth_mode
    if "smtp_auth_mode" in d and d["smtp_auth_mode"] is not None:
        auth_mode = d["smtp_auth_mode"] if d["smtp_auth_mode"] in ("login", "none") else "login"

    password = cfg.password
    if d.get("clear_smtp_password"):
        password = None
    elif (
        "smtp_password" in d and d["smtp_password"] is not None and str(d["smtp_password"]).strip()
    ):
        password = str(d["smtp_password"]).strip()

    return SmtpConfig(
        enabled=enabled,
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        starttls=starttls,
        implicit_tls=implicit_tls,
        validate_certs=validate_certs,
        auth_mode=auth_mode,
    )


async def persist_smtp_system_settings(
    db: AsyncSession,
    settings: Settings,
    *,
    enabled: bool | None = None,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    from_address: str | None = None,
    starttls: bool | None = None,
    implicit_tls: bool | None = None,
    validate_certs: bool | None = None,
    auth_mode: SmtpAuthMode | None = None,
    password: str | None = None,
    clear_password: bool = False,
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
        await _set(_SMTP_ENABLED, "true" if enabled else "false")
    if host is not None:
        changed = True
        await _set(_SMTP_HOST, host.strip())
    if port is not None:
        changed = True
        await _set(_SMTP_PORT, str(int(port)))
    if username is not None:
        changed = True
        await _set(_SMTP_USERNAME, username.strip())
    if from_address is not None:
        changed = True
        await _set(_SMTP_FROM, from_address.strip())
    if starttls is not None:
        changed = True
        await _set(_SMTP_STARTTLS, "true" if starttls else "false")
    if implicit_tls is not None:
        changed = True
        await _set(_SMTP_IMPLICIT_TLS, "true" if implicit_tls else "false")
    if validate_certs is not None:
        changed = True
        await _set(_SMTP_VALIDATE_CERTS, "true" if validate_certs else "false")
    if auth_mode is not None:
        changed = True
        await _set(_SMTP_AUTH_MODE, auth_mode)
    if clear_password:
        changed = True
        await db.execute(delete(SystemSetting).where(SystemSetting.key == _SMTP_PASSWORD_ENC))
    elif password is not None and password.strip():
        changed = True
        enc = encrypt_text(settings, password.strip())
        await _set(_SMTP_PASSWORD_ENC, enc)
    if changed:
        await db.commit()


async def send_smtp_message(
    cfg: SmtpConfig,
    *,
    to_addrs: list[str],
    subject: str,
    text_body: str,
) -> None:
    if not cfg.from_address:
        raise ValueError("SMTP from address is not configured")
    if not to_addrs:
        raise ValueError("No recipients")
    if cfg.starttls and cfg.implicit_tls:
        raise ValueError("Choose either STARTTLS (port 587) or implicit TLS (port 465), not both")
    if not smtp_uses_encrypted_transport(cfg):
        raise ValueError("SMTP transport must use STARTTLS or implicit TLS")

    msg = EmailMessage()
    msg["From"] = cfg.from_address
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(text_body)

    client = aiosmtplib.SMTP(
        hostname=cfg.host or "",
        port=cfg.port,
        use_tls=cfg.implicit_tls,
        validate_certs=cfg.validate_certs,
    )
    await client.connect()
    try:
        if cfg.starttls and not cfg.implicit_tls:
            await client.starttls()
        if cfg.auth_mode == "login":
            if not cfg.username or not cfg.password:
                raise ValueError("SMTP login authentication requires username and password")
            await client.login(cfg.username, cfg.password)
        await client.send_message(msg)
    finally:
        with contextlib.suppress(Exception):
            await client.quit()

    log.info("smtp.sent", to_count=len(to_addrs), subject=subject[:80])
