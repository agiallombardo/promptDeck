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


@pytest.mark.asyncio
async def test_logs_invalid_channel_rejected(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="super2@example.com",
                password_hash=hash_password("z"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "super2@example.com", "password": "z"},
    )
    token = login.json()["access_token"]
    r = await client.get(
        "/api/v1/admin/logs?channel=not_a_real_channel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_stats_and_audit_ok(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="stats-admin@example.com",
                password_hash=hash_password("s"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "stats-admin@example.com", "password": "s"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    s = await client.get("/api/v1/admin/stats", headers=h)
    assert s.status_code == 200
    body = s.json()
    assert body["users"] >= 1
    assert "presentations" in body

    a = await client.get("/api/v1/admin/audit", headers=h)
    assert a.status_code == 200
    assert "items" in a.json()


@pytest.mark.asyncio
async def test_logs_path_prefix_filter(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="prefix-admin@example.com",
                password_hash=hash_password("p"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "prefix-admin@example.com", "password": "p"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    await client.get("/health", headers=h)

    r = await client.get(
        "/api/v1/admin/logs?path_prefix=/api/v1/admin&limit=50",
        headers=h,
    )
    assert r.status_code == 200
    for row in r.json()["items"]:
        assert row["path"].startswith("/api/v1/admin")


@pytest.mark.asyncio
async def test_logs_event_contains_filter(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="event-admin@example.com",
                password_hash=hash_password("e"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "event-admin@example.com", "password": "e"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get(
        "/api/v1/admin/logs?event_contains=auth.login&limit=50",
        headers=h,
    )
    assert r.status_code == 200
    for row in r.json()["items"]:
        ev = row.get("event")
        assert ev is not None and "auth.login" in ev
