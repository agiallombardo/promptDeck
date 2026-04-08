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
