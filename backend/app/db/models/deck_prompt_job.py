from __future__ import annotations

import enum
import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class DeckPromptJobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class DeckPromptJob(Base):
    __tablename__ = "deck_prompt_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentation_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[DeckPromptJobStatus] = mapped_column(String(32), nullable=False)
    status_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    progress: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentation_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
