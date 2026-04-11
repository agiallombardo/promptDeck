from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.deck_prompt_job import DeckPromptJobStatus
from pydantic import BaseModel, Field


class DeckPromptJobCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16_000)


class DeckPromptJobRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    source_version_id: uuid.UUID
    status: DeckPromptJobStatus
    status_message: str | None
    progress: int
    error: str | None
    result_version_id: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
