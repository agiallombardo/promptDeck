from __future__ import annotations

from app.db.base import Base
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text(), nullable=False)
