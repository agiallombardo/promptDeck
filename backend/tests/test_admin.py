import uuid

import pytest
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logs_forbidden_for_non_admin(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="viewer2@example.com",
                password_hash=hash_password("x"),
                role=UserRole.viewer,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer2@example.com", "password": "x"},
    )
    token = login.json()["access_token"]
    r = await client.get("/api/v1/admin/logs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_logs_ok_for_admin(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="super@example.com",
                password_hash=hash_password("y"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "super@example.com", "password": "y"},
    )
    token = login.json()["access_token"]

    await client.get("/health", headers={"Authorization": f"Bearer {token}"})

    r = await client.get("/api/v1/admin/logs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1
