import uuid

import pytest
from app.config import get_settings
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_auth_config_exposes_local_login_in_tests(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/config")
    assert r.status_code == 200
    assert r.json()["local_password_auth_enabled"] is True


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nope@example.com", "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_and_me(client: AsyncClient) -> None:
    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="member@example.com",
                display_name="Member",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.user,
            )
        )
        await session.commit()

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "secret-pass-1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "member@example.com"
    assert body["user"]["role"] == "user"
    token = body["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["id"] == str(uid)


@pytest.mark.asyncio
async def test_refresh_rotates_cookie(client: AsyncClient) -> None:
    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="admin@example.com",
                display_name="Admin",
                password_hash=hash_password("admin-pass-1"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin-pass-1"},
    )
    assert login.status_code == 200
    assert "refresh_token" in client.cookies

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["user"]["email"] == "admin@example.com"


@pytest.mark.asyncio
async def test_last_login_updated(client: AsyncClient) -> None:
    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="viewer@example.com",
                password_hash=hash_password("v"),
                role=UserRole.user,
            )
        )
        await session.commit()

    await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "v"},
    )

    async with session_factory()() as session:
        row = (await session.execute(select(User).where(User.id == uid))).scalar_one()
        assert row.last_login_at is not None


@pytest.mark.asyncio
async def test_refresh_rejects_cross_site_origin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("PUBLIC_APP_URL", "http://app.local")
    get_settings.cache_clear()

    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="csrf-refresh@example.com",
                display_name="Refresh",
                password_hash=hash_password("secret-pass-9"),
                role=UserRole.user,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "csrf-refresh@example.com", "password": "secret-pass-9"},
    )
    assert login.status_code == 200

    bad = await client.post("/api/v1/auth/refresh", headers={"Origin": "http://evil.local"})
    assert bad.status_code == 403

    ok = await client.post("/api/v1/auth/refresh", headers={"Origin": "http://app.local"})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_refresh_allows_localhost_when_public_app_is_loopback(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dev: allow refresh when PUBLIC_APP_URL is 127.0.0.1 but Origin is localhost (same port)."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("PUBLIC_APP_URL", "http://127.0.0.1:5174")
    get_settings.cache_clear()

    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="loopback@example.com",
                display_name="Loop",
                password_hash=hash_password("loop-pass"),
                role=UserRole.user,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "loopback@example.com", "password": "loop-pass"},
    )
    assert login.status_code == 200

    refresh = await client.post("/api/v1/auth/refresh", headers={"Origin": "http://localhost:5174"})
    assert refresh.status_code == 200


@pytest.mark.asyncio
async def test_me_settings_clear_llm_provider(client: AsyncClient) -> None:
    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="settings-llm@example.com",
                display_name="Settings",
                password_hash=hash_password("p"),
                role=UserRole.user,
                llm_provider="openai",
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "settings-llm@example.com", "password": "p"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    patch = await client.patch(
        "/api/v1/auth/me/settings",
        headers=h,
        json={"clear_llm_provider": True, "llm_provider": "claude"},
    )
    assert patch.status_code == 200
    assert patch.json()["llm_provider"] is None

    get = await client.get("/api/v1/auth/me/settings", headers=h)
    assert get.status_code == 200
    assert get.json()["llm_provider"] is None
