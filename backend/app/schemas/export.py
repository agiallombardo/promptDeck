from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db.models.export_job import ExportFormat, ExportStatus
from pydantic import BaseModel, Field


class ExportCreate(BaseModel):
    version_id: uuid.UUID | None = None
    format: ExportFormat = ExportFormat.pdf
    scope: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class ExportJobRead(BaseModel):
    id: uuid.UUID
    presentation_id: uuid.UUID
    version_id: uuid.UUID
    format: ExportFormat
    status: ExportStatus
    output_path: str | None
    error: str | None
    progress: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
