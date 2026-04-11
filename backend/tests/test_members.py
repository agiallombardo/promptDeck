from __future__ import annotations

import uuid

import pytest
from app.config import get_settings
from app.db.models.system_setting import SystemSetting
from app.db.models.user import AuthProvider, User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_members_use_db_entra_tenant_when_env_missing(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENTRA_TENANT_ID", "")
    get_settings.cache_clear()

    owner_id = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            SystemSetting(
                key="entra_tenant_id",
                value="tenant-db",
            )
        )
        session.add(
            User(
                id=owner_id,
                email="owner-members@example.com",
                display_name="Owner",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.user,
                auth_provider=AuthProvider.entra,
                entra_tenant_id="tenant-db",
                entra_object_id="owner-oid",
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner-members@example.com", "password": "secret-pass-1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    pres = await client.post("/api/v1/presentations", headers=headers, json={"title": "Deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]

    create_member = await client.post(
        f"/api/v1/presentations/{pid}/members",
        headers=headers,
        json={
            "entra_object_id": "invitee-oid",
            "email": "invitee@example.com",
            "display_name": "Invitee",
            "user_type": "Member",
            "role": "user",
        },
    )
    assert create_member.status_code == 201, create_member.text
    assert create_member.json()["principal_tenant_id"] == "tenant-db"
