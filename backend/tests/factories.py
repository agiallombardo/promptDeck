"""Minimal Polyfactory SQLAlchemy factories for tests."""

from __future__ import annotations

import uuid

from app.db.models.user import User, UserRole
from polyfactory import Use
from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory


class UserFactory(SQLAlchemyFactory[User]):
    __model__ = User
    __check_model__ = False
    __set_relationships__ = False

    id = Use(lambda: uuid.uuid4())
    email = Use(lambda: f"user-{uuid.uuid4().hex[:8]}@example.com")
    display_name = "Test user"
    password_hash = "x" * 60
    role = UserRole.editor
