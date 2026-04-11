from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.presentation_member import PresentationMemberRole
from pydantic import BaseModel, EmailStr, Field


class PresentationMemberCreate(BaseModel):
    entra_object_id: str = Field(min_length=1, max_length=64)
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=200)
    user_type: str | None = Field(default=None, max_length=32)
    role: PresentationMemberRole


class PresentationMemberUpdate(BaseModel):
    role: PresentationMemberRole


class PresentationMemberRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    role: PresentationMemberRole
    principal_tenant_id: str
    principal_entra_object_id: str
    principal_email: str
    principal_display_name: str | None
    principal_user_type: str | None
    user_id: uuid.UUID | None
    granted_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresentationMemberListResponse(BaseModel):
    items: list[PresentationMemberRead]
