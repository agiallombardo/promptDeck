from __future__ import annotations

import uuid

from app.db.base import Base
from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column


class DeckPromptJobArtifact(Base):
    __tablename__ = "deck_prompt_job_artifacts"

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("deck_prompt_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentation_source_artifacts.id", ondelete="CASCADE"),
        primary_key=True,
    )
