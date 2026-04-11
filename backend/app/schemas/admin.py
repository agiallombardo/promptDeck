from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class AppLogRead(BaseModel):
    """`app_logs.logger` is exposed as `channel` in the API."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    ts: datetime
    level: str
    event: str | None
    channel: str = Field(validation_alias="logger", description="http | auth | audit | script")
    request_id: str | None
    user_id: uuid.UUID | None
    path: str
    method: str
    status_code: int | None
    latency_ms: int | None
    payload: dict[str, Any] | None


class AppLogListResponse(BaseModel):
    items: list[AppLogRead]
    next_cursor: int | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    ts: datetime
    actor_id: uuid.UUID | None
    action: str
    target_kind: str | None
    target_id: uuid.UUID | None
    metadata: dict[str, Any] | None = Field(validation_alias="metadata_")
    ip: str | None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    last_login_at: datetime | None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserRead]


class AdminPresentationRow(BaseModel):
    id: uuid.UUID
    title: str
    owner_id: uuid.UUID
    owner_email: str
    current_version_id: uuid.UUID | None
    version_count: int
    updated_at: datetime


class AdminPresentationListResponse(BaseModel):
    items: list[AdminPresentationRow]


class AdminExportJobRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    presentation_title: str
    version_id: uuid.UUID
    format: str
    status: str
    progress: int
    error: str | None
    created_by: uuid.UUID
    created_at: datetime
    finished_at: datetime | None


class AdminExportJobListResponse(BaseModel):
    items: list[AdminExportJobRead]


class AdminStatsRead(BaseModel):
    users: int
    presentations: int
    versions: int
    export_jobs: int
    audit_events_24h: int
    app_log_rows_24h: int


class AdminSetupRead(BaseModel):
    local_password_auth_enabled: bool
    entra_enabled: bool
    entra_tenant_id_configured: bool
    entra_client_id_configured: bool
    entra_client_secret_configured: bool
    entra_login_ready: bool
    smtp_enabled: bool
    smtp_ready: bool
    public_app_url: str
    public_api_url: str
    entra_redirect_uri: str


class AdminEntraSettingsRead(BaseModel):
    entra_enabled: bool
    entra_tenant_id: str | None
    entra_client_id: str | None
    entra_client_secret_configured: bool
    entra_authority_host: str | None
    public_api_url: str
    entra_redirect_uri: str


class AdminEntraSettingsPatch(BaseModel):
    entra_enabled: bool | None = None
    entra_tenant_id: str | None = Field(default=None, max_length=64)
    entra_client_id: str | None = Field(default=None, max_length=128)
    entra_client_secret: str | None = Field(default=None, max_length=512)
    clear_entra_client_secret: bool = False
    entra_authority_host: str | None = Field(default=None, max_length=256)


class AdminSmtpSettingsRead(BaseModel):
    smtp_enabled: bool
    smtp_host: str | None = None
    smtp_port: int
    smtp_username: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool
    smtp_implicit_tls: bool
    smtp_validate_certs: bool
    smtp_auth_mode: Literal["login", "none"]
    smtp_password_configured: bool
    smtp_password_stored_encrypted: bool = Field(
        default=True,
        description=(
            "SMTP password is never returned; at rest it is encrypted "
            "(Fernet, same key as Entra secrets)."
        ),
    )
    smtp_ready: bool


class AdminSmtpSettingsPatch(BaseModel):
    smtp_enabled: bool | None = None
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, max_length=320)
    smtp_from: EmailStr | None = None
    smtp_starttls: bool | None = None
    smtp_implicit_tls: bool | None = None
    smtp_validate_certs: bool | None = None
    smtp_auth_mode: Literal["login", "none"] | None = None
    smtp_password: str | None = Field(
        default=None,
        max_length=512,
        description="Written only on save; stored encrypted server-side and never echoed back.",
    )
    clear_smtp_password: bool = False

    @model_validator(mode="after")
    def tls_not_both(self) -> AdminSmtpSettingsPatch:
        if self.smtp_starttls is True and self.smtp_implicit_tls is True:
            raise ValueError("Use STARTTLS (e.g. port 587) or implicit TLS (port 465), not both")
        return self


class AdminSmtpTestRequest(BaseModel):
    """Optional override; defaults to the signed-in admin user's email."""

    to: EmailStr | None = None


class AdminSmtpTestResponse(BaseModel):
    ok: bool = True
    to: EmailStr


class AdminLlmSettingsRead(BaseModel):
    """LiteLLM or any OpenAI-compatible proxy (system default for future LLM features)."""

    litellm_api_base: str | None = Field(
        default=None,
        description="Effective base URL (database override, else LITELLM_API_BASE env).",
    )
    litellm_api_base_configured: bool = Field(
        default=False,
        description="True when a non-empty base URL is set (DB or env).",
    )
    litellm_api_key_configured: bool = False
    litellm_api_key_stored_encrypted: bool = Field(
        default=True,
        description="API key is never returned; stored encrypted (Fernet, same as other secrets).",
    )


class AdminLlmSettingsPatch(BaseModel):
    litellm_api_base: str | None = Field(
        default=None,
        max_length=512,
        description=(
            "OpenAI-compatible API root (e.g. https://litellm.internal/v1). "
            "Empty string clears DB override."
        ),
    )
    litellm_api_key: str | None = Field(
        default=None,
        max_length=4096,
        description="Written only on save; stored encrypted server-side and never echoed back.",
    )
    clear_litellm_api_key: bool = False
    clear_litellm_api_base: bool = Field(
        default=False,
        description="Remove DB base URL; use LITELLM_API_BASE env only.",
    )
