from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.share_link import ShareRole
from pydantic import BaseModel, Field


class ShareCreate(BaseModel):
    role: ShareRole = Field(default=ShareRole.viewer)
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class ShareRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    role: ShareRole
    expires_at: datetime | None
    revoked_at: datetime | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareCreated(ShareRead):
    """Returned once when creating a link; includes the secret token."""

    token: str = Field(min_length=1)


class ShareExchangeRequest(BaseModel):
    token: str = Field(min_length=1, max_length=500)


class ShareExchangeResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    presentation_id: uuid.UUID
    role: ShareRole


class ShareListResponse(BaseModel):
    items: list[ShareRead]
