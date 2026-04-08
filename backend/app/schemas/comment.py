from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.comment_thread import ThreadStatus
from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=50_000)


class ThreadCreate(BaseModel):
    version_id: uuid.UUID
    slide_index: int = Field(ge=0)
    anchor_x: float = Field(ge=0, le=1)
    anchor_y: float = Field(ge=0, le=1)
    first_comment: str = Field(min_length=1, max_length=50_000)


class ThreadPatch(BaseModel):
    status: ThreadStatus


class CommentRead(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    author_display_name: str | None = None
    body: str
    body_format: str
    created_at: datetime
    edited_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ThreadRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    version_id: uuid.UUID
    slide_index: int
    anchor_x: float
    anchor_y: float
    status: ThreadStatus
    created_by: uuid.UUID
    created_at: datetime
    resolved_at: datetime | None
    comments: list[CommentRead] = []

    model_config = ConfigDict(from_attributes=True)


class ThreadListResponse(BaseModel):
    items: list[ThreadRead]
