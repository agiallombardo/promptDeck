from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from app.schemas.deck_prompt import DeckPromptJobRead
from app.services.acl import PresentationAccess
from pydantic import BaseModel, Field


class PresentationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    kind: str = Field(default="deck", pattern="^(deck|diagram)$")
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
    kind: str
    description: str | None
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    current_user_role: PresentationAccess | None = None
    current_version: VersionRead | None = None

    model_config = {"from_attributes": True}


class PresentationListResponse(BaseModel):
    items: list[PresentationRead]
    next_cursor: str | None = None


class PresentationGenerateFromPromptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    prompt: str = Field(min_length=1, max_length=16_000)
    description: str | None = Field(default=None, max_length=10_000)


class PresentationGenerateFromPromptResponse(BaseModel):
    presentation: PresentationRead
    job: DeckPromptJobRead


class EmbedResponse(BaseModel):
    iframe_src: str
    version_id: uuid.UUID
    slide_count: int


class DiagramDocumentRead(BaseModel):
    version_id: uuid.UUID
    document: dict[str, Any]


class DiagramDocumentWrite(BaseModel):
    document: dict[str, Any]


class DiagramThumbnailResponse(BaseModel):
    version_id: uuid.UUID
    png_src: str
    jpg_src: str


class PresentationCodeRead(BaseModel):
    version_id: uuid.UUID
    html: str
    css: str
    js: str


class PresentationCodeUpdate(BaseModel):
    base_version_id: uuid.UUID
    html: str = Field(min_length=1, max_length=2_000_000)
    css: str = Field(default="", max_length=500_000)
    js: str = Field(default="", max_length=500_000)


class PresentationSourceArtifactRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    original_filename: str
    content_type: str | None
    size_bytes: int
    sha256: str
    intent: Literal["embed", "inspire"]
    created_at: datetime

    model_config = {"from_attributes": True}


class PresentationSourceArtifactUpdate(BaseModel):
    intent: Literal["embed", "inspire"]


class PresentationSourceArtifactListResponse(BaseModel):
    items: list[PresentationSourceArtifactRead]
