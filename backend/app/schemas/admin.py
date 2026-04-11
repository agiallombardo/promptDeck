from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    public_app_url: str
    public_api_url: str
    entra_redirect_uri: str
