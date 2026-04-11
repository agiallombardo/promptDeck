"""Merge env Settings with DB system_settings for outbound SMTP (e.g. Microsoft 365 relay)."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from email.message import EmailMessage

import aiosmtplib
import structlog
from app.config import Settings
from app.db.models.system_setting import SystemSetting
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


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


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
    )


def smtp_password_configured(settings: Settings, kv: dict[str, str]) -> bool:
    if settings.smtp_password and settings.smtp_password.strip():
        return True
    enc = kv.get(_SMTP_PASSWORD_ENC, "")
    return bool(enc and enc.strip())


def smtp_ready(cfg: SmtpConfig) -> bool:
    return bool(
        cfg.enabled
        and cfg.host
        and cfg.from_address
        and cfg.password
        and cfg.port
        and not (cfg.starttls and cfg.implicit_tls)
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

    msg = EmailMessage()
    msg["From"] = cfg.from_address
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(text_body)

    client = aiosmtplib.SMTP(
        hostname=cfg.host or "",
        port=cfg.port,
        use_tls=cfg.implicit_tls,
    )
    await client.connect()
    try:
        if cfg.starttls and not cfg.implicit_tls:
            await client.starttls()
        if cfg.username and cfg.password:
            await client.login(cfg.username, cfg.password)
        await client.send_message(msg)
    finally:
        with contextlib.suppress(Exception):
            await client.quit()

    log.info("smtp.sent", to_count=len(to_addrs), subject=subject[:80])
