from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from app.db.models.deck_prompt_job import DeckPromptJobStatus
from pydantic import BaseModel, Field, field_validator


class DeckPromptJobCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16_000)
    source_artifact_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("source_artifact_ids")
    @classmethod
    def _normalize_artifact_ids(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) > 20:
            raise ValueError("At most 20 source artifacts per job")
        seen: set[uuid.UUID] = set()
        out: list[uuid.UUID] = []
        for x in v:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out


class DeckPromptJobRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    source_version_id: uuid.UUID
    job_type: Literal["deck_edit", "deck_generate", "diagram_generate"] = "deck_edit"
    is_generation: bool = False
    status: DeckPromptJobStatus
    status_message: str | None
    progress: int
    error: str | None
    result_version_id: uuid.UUID | None
    llm_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
