from __future__ import annotations

import uuid
from datetime import datetime

from app.services.acl import PresentationAccess
from pydantic import BaseModel, Field


class PresentationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10_000)


class PresentationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None


class SlideRead(BaseModel):
    id: uuid.UUID
    slide_index: int
    selector: str
    title: str | None

    model_config = {"from_attributes": True}


class VersionRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    version_number: int
    origin: str
    storage_kind: str
    entry_path: str
    sha256: str
    size_bytes: int
    created_at: datetime
    slides: list[SlideRead] = []

    model_config = {"from_attributes": True}


class PresentationRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    current_user_role: PresentationAccess | None = None
    current_version: VersionRead | None = None

    model_config = {"from_attributes": True}


class PresentationListResponse(BaseModel):
    items: list[PresentationRead]


class EmbedResponse(BaseModel):
    iframe_src: str
    version_id: uuid.UUID
    slide_count: int
