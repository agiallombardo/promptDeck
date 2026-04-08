from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db.base import Base
from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditLog(Base):
    """Security-relevant events (separate from `app_logs` ring buffer)."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
