from __future__ import annotations

import asyncio
import functools
import uuid

import pytest
from app.config import get_settings
from app.db.models.user import AuthProvider, User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient

SAMPLE_HTML = b"""<!DOCTYPE html><html><body><section>A</section></body></html>"""


@functools.lru_cache(maxsize=1)
def _playwright_chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


@pytest.fixture
async def editor_client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("ENTRA_TENANT_ID", "tenant-123")
    get_settings.cache_clear()

    from app.db.base import Base
    from app.db.session import dispose_engine, get_engine
    from app.main import app

    await dispose_engine()
    get_settings.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    owner_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    async with session_factory()() as session:
        session.add_all(
            [
                User(
                    id=owner_id,
                    email="share@example.com",
                    display_name="Share",
                    password_hash=hash_password("secret-pass-1"),
                    role=UserRole.user,
                ),
                User(
                    id=recipient_id,
                    email="recipient@example.com",
                    display_name="Recipient",
                    password_hash=hash_password("secret-pass-2"),
                    role=UserRole.user,
                    auth_provider=AuthProvider.entra,
                    entra_tenant_id="tenant-123",
                    entra_object_id="recipient-oid",
                ),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "share@example.com", "password": "secret-pass-1"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac, transport

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_member_share_grants_reader_access(editor_client) -> None:
    c, transport = editor_client
    p = await c.post("/api/v1/presentations", json={"title": "Shared"})
    assert p.status_code == 201
    pid = p.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("x.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    member = await c.post(
        f"/api/v1/presentations/{pid}/members",
        json={
            "entra_object_id": "recipient-oid",
            "email": "recipient@example.com",
            "display_name": "Recipient",
            "user_type": "Member",
            "role": "user",
        },
    )
    assert member.status_code == 201

    async with AsyncClient(transport=transport, base_url="http://test") as recipient:
        login = await recipient.post(
            "/api/v1/auth/login",
            json={"email": "recipient@example.com", "password": "secret-pass-2"},
        )
        assert login.status_code == 200
        recipient.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
        g = await recipient.get(f"/api/v1/presentations/{pid}")
        assert g.status_code == 200
        assert g.json()["title"] == "Shared"
        assert g.json()["current_user_role"] == "user"


@pytest.mark.asyncio
async def test_share_link_exchange_grants_comment_access(editor_client) -> None:
    c, transport = editor_client
    p = await c.post("/api/v1/presentations", json={"title": "Share link deck"})
    assert p.status_code == 201
    pid = p.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("x.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201
    version_id = up.json()["id"]

    create_link = await c.post(
        f"/api/v1/presentations/{pid}/share-links",
        json={"role": "commenter", "expires_in_hours": 24},
    )
    assert create_link.status_code == 201, create_link.text
    token = create_link.json()["share_token"]

    exchange = await c.post(
        "/api/v1/share-links/exchange",
        json={"token": token},
    )
    assert exchange.status_code == 200, exchange.text
    share_access = exchange.json()["access_token"]

    async with AsyncClient(transport=transport, base_url="http://test") as shared_client:
        shared_client.headers.update({"Authorization": f"Bearer {share_access}"})
        g = await shared_client.get(f"/api/v1/presentations/{pid}")
        assert g.status_code == 200
        assert g.json()["current_user_role"] == "commenter"

        thread = await shared_client.post(
            f"/api/v1/presentations/{pid}/threads",
            json={
                "version_id": version_id,
                "slide_index": 0,
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "first_comment": "share link comment",
            },
        )
        assert thread.status_code == 201, thread.text


@pytest.mark.asyncio
async def test_export_job_stub(editor_client) -> None:
    if not _playwright_chromium_available():
        pytest.skip("Playwright Chromium missing; run: uv run playwright install (from backend/)")

    c, _transport = editor_client
    p = await c.post("/api/v1/presentations", json={"title": "Ex"})
    pid = p.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("x.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    j = await c.post(
        f"/api/v1/presentations/{pid}/exports",
        json={"format": "pdf"},
    )
    assert j.status_code == 202
    jid = j.json()["id"]

    for _ in range(200):
        r = await c.get(f"/api/v1/exports/{jid}")
        assert r.status_code == 200
        if r.json()["status"] == "succeeded":
            assert r.json()["output_path"] is not None
            pdf = await c.get(f"/api/v1/exports/{jid}/file")
            assert pdf.status_code == 200
            assert pdf.content[:4] == b"%PDF"
            return
        if r.json()["status"] == "failed":
            raise AssertionError(r.json().get("error") or "export failed")
        await asyncio.sleep(0.1)
    raise AssertionError("export did not complete")


@pytest.mark.asyncio
async def test_export_single_html_job(editor_client) -> None:
    c, _transport = editor_client
    p = await c.post("/api/v1/presentations", json={"title": "HtmlEx"})
    pid = p.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("x.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    j = await c.post(
        f"/api/v1/presentations/{pid}/exports",
        json={"format": "single_html"},
    )
    assert j.status_code == 202
    jid = j.json()["id"]

    for _ in range(200):
        r = await c.get(f"/api/v1/exports/{jid}")
        assert r.status_code == 200
        if r.json()["status"] == "succeeded":
            dl = await c.get(f"/api/v1/exports/{jid}/file")
            assert dl.status_code == 200
            assert b"<!DOCTYPE html>" in dl.content or b"<html" in dl.content
            assert dl.headers.get("content-type", "").startswith("text/html")
            return
        if r.json()["status"] == "failed":
            raise AssertionError(r.json().get("error") or "export failed")
        await asyncio.sleep(0.05)
    raise AssertionError("html export did not complete")
