"""Tests for presentation ACL resolution."""

from __future__ import annotations

import uuid

import pytest
from app.config import get_settings
from app.db.models.presentation import Presentation
from app.db.models.presentation_member import PresentationMember, PresentationMemberRole
from app.db.models.user import AuthProvider, User, UserRole
from app.db.session import dispose_engine, get_engine, session_factory
from app.services.acl import PresentationAccess, resolve_access


@pytest.fixture
async def acl_db(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "store"))
    get_settings.cache_clear()

    from app.db.base import Base

    await dispose_engine()
    get_settings.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_resolve_access_picks_editor_when_duplicate_member_rows(acl_db) -> None:
    owner_id = uuid.uuid4()
    granter_id = uuid.uuid4()
    member_id = uuid.uuid4()
    pres_id = uuid.uuid4()

    async with session_factory()() as session:
        session.add_all(
            [
                User(
                    id=owner_id,
                    email="owner-acl@example.com",
                    password_hash="x" * 60,
                    role=UserRole.user,
                ),
                User(
                    id=granter_id,
                    email="granter-acl@example.com",
                    password_hash="x" * 60,
                    role=UserRole.user,
                ),
                User(
                    id=member_id,
                    email="member-acl@example.com",
                    password_hash="x" * 60,
                    role=UserRole.user,
                    auth_provider=AuthProvider.entra,
                    entra_tenant_id="tenant-acl",
                    entra_object_id="oid-primary",
                ),
            ]
        )
        session.add(
            Presentation(
                id=pres_id,
                owner_id=owner_id,
                title="ACL test deck",
            )
        )
        session.add_all(
            [
                PresentationMember(
                    presentation_id=pres_id,
                    role=PresentationMemberRole.user,
                    principal_tenant_id="tenant-acl",
                    principal_entra_object_id="oid-stale",
                    principal_email="member-acl@example.com",
                    user_id=member_id,
                    granted_by=granter_id,
                ),
                PresentationMember(
                    presentation_id=pres_id,
                    role=PresentationMemberRole.editor,
                    principal_tenant_id="tenant-acl",
                    principal_entra_object_id="oid-primary",
                    principal_email="member-acl@example.com",
                    user_id=member_id,
                    granted_by=granter_id,
                ),
            ]
        )
        await session.commit()

    async with session_factory()() as session:
        pres = await session.get(Presentation, pres_id)
        assert pres is not None
        member_user = await session.get(User, member_id)
        assert member_user is not None
        access = await resolve_access(session, pres, member_user)

    assert access == PresentationAccess.editor
