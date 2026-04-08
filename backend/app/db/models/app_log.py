from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.db.base import Base
from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class AppLog(Base):
    __tablename__ = "app_logs"

    # SQLite requires INTEGER PRIMARY KEY for autoincrement; keep BIGINT on Postgres.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    event: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logger: Mapped[str] = mapped_column(String(128), nullable=False, default="app")
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
