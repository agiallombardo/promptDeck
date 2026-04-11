from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.share_link import ShareRole
from pydantic import BaseModel, Field


class ShareLinkCreate(BaseModel):
    role: ShareRole = ShareRole.viewer
    expires_in_hours: int | None = Field(default=None, ge=1, le=168)
    note: str | None = Field(default=None, max_length=500)


class ShareLinkRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    role: ShareRole
    expires_at: datetime | None
    revoked_at: datetime | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareLinkCreateResponse(ShareLinkRead):
    share_token: str
    share_url: str


class ShareLinkListResponse(BaseModel):
    items: list[ShareLinkRead]


class ShareLinkExchangeRequest(BaseModel):
    token: str = Field(min_length=12, max_length=512)


class ShareLinkExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    presentation_id: uuid.UUID
    role: ShareRole
