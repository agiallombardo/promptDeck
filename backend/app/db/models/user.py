from __future__ import annotations

import enum
import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, Enum, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class UserRole(enum.StrEnum):
    admin = "admin"
    user = "user"


class AuthProvider(enum.StrEnum):
    local = "local"
    entra = "entra"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_entra_identity",
            "entra_tenant_id",
            "entra_object_id",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda c: [e.value for e in c], native_enum=False),
        nullable=False,
        default=UserRole.user,
    )
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider, values_callable=lambda c: [e.value for e in c], native_enum=False),
        nullable=False,
        default=AuthProvider.local,
    )
    entra_tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entra_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entra_user_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entra_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_api_key_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
