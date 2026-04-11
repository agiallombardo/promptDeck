from __future__ import annotations

import enum
import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class PresentationMemberRole(enum.StrEnum):
    editor = "editor"
    user = "user"


class PresentationMember(Base):
    __tablename__ = "presentation_members"
    __table_args__ = (
        Index(
            "ix_presentation_members_identity",
            "presentation_id",
            "principal_tenant_id",
            "principal_entra_object_id",
            unique=True,
        ),
        Index("ix_presentation_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("presentations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[PresentationMemberRole] = mapped_column(
        Enum(
            PresentationMemberRole,
            values_callable=lambda c: [e.value for e in c],
            native_enum=False,
        ),
        nullable=False,
    )
    principal_tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_entra_object_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_email: Mapped[str] = mapped_column(String(320), nullable=False)
    principal_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    principal_user_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
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
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
