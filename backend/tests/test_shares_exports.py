from __future__ import annotations

import asyncio
import uuid

import pytest
from app.config import get_settings
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient

SAMPLE_HTML = b"""<!DOCTYPE html><html><body><section>A</section></body></html>"""


@pytest.fixture
async def editor_client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "store"))
    get_settings.cache_clear()

    from app.db.base import Base
    from app.db.session import dispose_engine, get_engine
    from app.main import app

    await dispose_engine()
    get_settings.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    uid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=uid,
                email="share@example.com",
                display_name="Share",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.editor,
            )
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
async def test_share_create_exchange_and_reader_access(editor_client) -> None:
    c, transport = editor_client
    p = await c.post("/api/v1/presentations", json={"title": "Shared"})
    assert p.status_code == 201
    pid = p.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("x.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    sh = await c.post(
        f"/api/v1/presentations/{pid}/shares",
        json={"role": "viewer"},
    )
    assert sh.status_code == 201
    secret = sh.json()["token"]

    async with AsyncClient(transport=transport, base_url="http://test") as exc:
        ex = await exc.post("/api/v1/shares/exchange", json={"token": secret})
    assert ex.status_code == 200
    share_token = ex.json()["access_token"]

    async with AsyncClient(transport=transport, base_url="http://test") as anon:
        anon.headers.update({"Authorization": f"Bearer {share_token}"})
        g = await anon.get(f"/api/v1/presentations/{pid}")
        assert g.status_code == 200
        assert g.json()["title"] == "Shared"


@pytest.mark.asyncio
async def test_export_job_stub(editor_client) -> None:
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

    for _ in range(50):
        r = await c.get(f"/api/v1/exports/{jid}")
        assert r.status_code == 200
        if r.json()["status"] == "succeeded":
            assert r.json()["output_path"] is not None
            return
        await asyncio.sleep(0.05)
    raise AssertionError("export did not complete")
