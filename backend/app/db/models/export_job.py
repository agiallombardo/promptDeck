from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


class ExportFormat(enum.StrEnum):
    pdf = "pdf"
    single_html = "single_html"


class ExportStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentation_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[ExportFormat] = mapped_column(
        String(32),
        nullable=False,
    )
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    options: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    status: Mapped[ExportStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ExportStatus.queued,
    )
    output_path: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    progress: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
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
