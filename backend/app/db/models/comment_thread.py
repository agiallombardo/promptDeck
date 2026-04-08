from __future__ import annotations

import enum
import uuid
from datetime import datetime

from app.db.base import Base
from app.db.models.user import User
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ThreadStatus(enum.StrEnum):
    open = "open"
    resolved = "resolved"


class CommentThread(Base):
    __tablename__ = "comment_threads"

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
    slide_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    anchor_x: Mapped[float] = mapped_column(Float(), nullable=False)
    anchor_y: Mapped[float] = mapped_column(Float(), nullable=False)
    status: Mapped[ThreadStatus] = mapped_column(
        Enum(ThreadStatus, values_callable=lambda c: [e.value for e in c], native_enum=False),
        nullable=False,
        default=ThreadStatus.open,
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
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comments: Mapped[list[Comment]] = relationship(
        "Comment",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("comment_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    body_format: Mapped[str] = mapped_column(String(32), nullable=False, default="markdown")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    thread: Mapped[CommentThread] = relationship("CommentThread", back_populates="comments")
    author: Mapped[User] = relationship(foreign_keys=[author_id])
