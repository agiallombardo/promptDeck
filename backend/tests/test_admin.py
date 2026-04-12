import uuid
from unittest.mock import AsyncMock, patch

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
                role=UserRole.user,
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
async def test_deck_prompt_jobs_admin_forbidden_for_non_admin(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="viewer-dpj@example.com",
                password_hash=hash_password("x"),
                role=UserRole.user,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer-dpj@example.com", "password": "x"},
    )
    token = login.json()["access_token"]
    r = await client.get(
        "/api/v1/admin/deck-prompt-jobs",
        headers={"Authorization": f"Bearer {token}"},
    )
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
    assert "deck_prompt_jobs" in body
    assert "deck_prompt_jobs_24h" in body
    assert "llm_total_tokens_24h" in body

    dpj = await client.get("/api/v1/admin/deck-prompt-jobs", headers=h)
    assert dpj.status_code == 200
    assert "items" in dpj.json()

    a = await client.get("/api/v1/admin/audit", headers=h)
    assert a.status_code == 200
    audit_body = a.json()
    assert "items" in audit_body
    for row in audit_body["items"]:
        assert "actor_email" in row
        assert "actor_display_name" in row
    assert any(row.get("actor_email") for row in audit_body["items"])


@pytest.mark.asyncio
async def test_admin_setup_ok(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="setup-admin@example.com",
                password_hash=hash_password("setup"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "setup-admin@example.com", "password": "setup"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    s = await client.get("/api/v1/admin/setup", headers=h)
    assert s.status_code == 200
    body = s.json()
    assert "entra_redirect_uri" in body
    assert "public_app_url" in body
    assert "entra_login_ready" in body
    assert "smtp_enabled" in body
    assert "smtp_ready" in body


@pytest.mark.asyncio
async def test_admin_smtp_settings_get_defaults(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="smtp-admin@example.com",
                password_hash=hash_password("smtp"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "smtp-admin@example.com", "password": "smtp"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/v1/admin/settings/smtp", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["smtp_enabled"] is False
    assert data["smtp_ready"] is False
    assert data["smtp_password_configured"] is False
    assert data["smtp_validate_certs"] is True
    assert data["smtp_auth_mode"] == "login"
    assert data["smtp_password_stored_encrypted"] is True


@pytest.mark.asyncio
async def test_admin_smtp_settings_patch_and_test_mocked(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="smtp-patch@example.com",
                password_hash=hash_password("patch"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "smtp-patch@example.com", "password": "patch"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    p = await client.patch(
        "/api/v1/admin/settings/smtp",
        headers=h,
        json={
            "smtp_enabled": True,
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "smtp_username": "relay@example.com",
            "smtp_from": "relay@example.com",
            "smtp_starttls": True,
            "smtp_implicit_tls": False,
            "smtp_validate_certs": True,
            "smtp_auth_mode": "login",
            "smtp_password": "secret-smtp-pass",
        },
    )
    assert p.status_code == 200, p.text
    assert p.json()["smtp_ready"] is True

    with patch(
        "app.routers.admin.send_smtp_message",
        new_callable=AsyncMock,
    ) as send_mock:
        t = await client.post("/api/v1/admin/settings/smtp/test", headers=h, json={})
        assert t.status_code == 200, t.text
        assert t.json()["to"] == "smtp-patch@example.com"
        send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_admin_smtp_rejects_plain_transport_when_enabled(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="smtp-plain@example.com",
                password_hash=hash_password("plain"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "smtp-plain@example.com", "password": "plain"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    bad = await client.patch(
        "/api/v1/admin/settings/smtp",
        headers=h,
        json={
            "smtp_enabled": True,
            "smtp_host": "insecure.example.com",
            "smtp_port": 25,
            "smtp_username": "u@example.com",
            "smtp_from": "u@example.com",
            "smtp_starttls": False,
            "smtp_implicit_tls": False,
            "smtp_auth_mode": "login",
            "smtp_password": "x",
        },
    )
    assert bad.status_code == 400
    detail = bad.json()["detail"].lower()
    assert "unencrypted" in detail or "exactly one" in detail


@pytest.mark.asyncio
async def test_admin_smtp_auth_none_no_password_ready(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="smtp-relay@example.com",
                password_hash=hash_password("relay"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "smtp-relay@example.com", "password": "relay"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    p = await client.patch(
        "/api/v1/admin/settings/smtp",
        headers=h,
        json={
            "smtp_enabled": True,
            "smtp_host": "relay.internal",
            "smtp_port": 587,
            "smtp_username": None,
            "smtp_from": "app@example.com",
            "smtp_starttls": True,
            "smtp_implicit_tls": False,
            "smtp_auth_mode": "none",
            "smtp_validate_certs": True,
        },
    )
    assert p.status_code == 200, p.text
    assert p.json()["smtp_ready"] is True
    assert p.json()["smtp_auth_mode"] == "none"
    assert p.json()["smtp_password_configured"] is False


@pytest.mark.asyncio
async def test_admin_smtp_test_rejects_when_not_ready(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="smtp-nope@example.com",
                password_hash=hash_password("nope"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "smtp-nope@example.com", "password": "nope"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    t = await client.post("/api/v1/admin/settings/smtp/test", headers=h, json={})
    assert t.status_code == 400


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


@pytest.mark.asyncio
async def test_admin_llm_settings_get_and_patch(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="llm-admin@example.com",
                password_hash=hash_password("llm"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "llm-admin@example.com", "password": "llm"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    g = await client.get("/api/v1/admin/settings/llm", headers=h)
    assert g.status_code == 200
    data = g.json()
    assert data["deck_llm_provider"] == "litellm"
    assert data["litellm_api_key_configured"] is False
    assert "litellm_api_base" in data

    p = await client.patch(
        "/api/v1/admin/settings/llm",
        headers=h,
        json={
            "litellm_api_base": "https://litellm.internal/v1",
            "litellm_api_key": "sk-test-key",
        },
    )
    assert p.status_code == 200, p.text
    assert p.json()["litellm_api_base"] == "https://litellm.internal/v1"
    assert p.json()["litellm_api_key_configured"] is True

    c = await client.patch(
        "/api/v1/admin/settings/llm",
        headers=h,
        json={"clear_litellm_api_key": True},
    )
    assert c.status_code == 200
    assert c.json()["litellm_api_key_configured"] is False


@pytest.mark.asyncio
async def test_admin_llm_settings_rejects_invalid_api_base(client: AsyncClient) -> None:
    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="llm-invalid@example.com",
                password_hash=hash_password("llm-invalid"),
                role=UserRole.admin,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "llm-invalid@example.com", "password": "llm-invalid"},
    )
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    bad = await client.patch(
        "/api/v1/admin/settings/llm",
        headers=h,
        json={"litellm_api_base": "ftp://bad.example.com/v1"},
    )
    assert bad.status_code == 400
