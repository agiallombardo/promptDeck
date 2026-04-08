from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Presentation(Base):
    __tablename__ = "presentations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Validated in app (avoid circular create_all FK: presentations <-> presentation_versions).
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    versions: Mapped[list[PresentationVersion]] = relationship(
        "PresentationVersion",
        back_populates="presentation",
    )


class PresentationVersion(Base):
    __tablename__ = "presentation_versions"
    __table_args__ = (
        UniqueConstraint("presentation_id", "version_number", name="uq_pres_version_num"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_prefix: Mapped[str] = mapped_column(String(1024), nullable=False)
    entry_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    presentation: Mapped[Presentation] = relationship("Presentation", back_populates="versions")
    slides: Mapped[list[Slide]] = relationship(
        "Slide",
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="Slide.slide_index",
    )


class Slide(Base):
    __tablename__ = "slides"
    __table_args__ = (UniqueConstraint("version_id", "index", name="uq_slide_version_idx"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentation_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_index: Mapped[int] = mapped_column("index", Integer(), nullable=False)
    selector: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    version: Mapped[PresentationVersion] = relationship(
        "PresentationVersion",
        back_populates="slides",
    )
