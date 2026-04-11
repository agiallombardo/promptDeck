from __future__ import annotations

import io
import uuid
import zipfile
from urllib.parse import parse_qs, urlparse

import pytest
from app.config import get_settings
from app.db.models.audit_log import AuditLog
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

SAMPLE_HTML = b"""<!DOCTYPE html>
<html><head><title>T</title></head>
<body><section><p>One</p></section><section><p>Two</p></section></body></html>
"""


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
                email="pres@example.com",
                display_name="Pres",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.editor,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "pres@example.com", "password": "secret-pass-1"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_upload_embed_and_serve_asset(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Deck"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["version_number"] == 1
    assert len(body["slides"]) >= 1

    emb = await c.get(f"/api/v1/presentations/{pid}/embed")
    assert emb.status_code == 200
    iframe_src = emb.json()["iframe_src"]
    parsed = urlparse(iframe_src)
    assert parsed.path.startswith("/a/")
    q = parse_qs(parsed.query)
    assert "exp" in q and "sig" in q and "sub" in q and "role" in q

    asset_path = parsed.path.removeprefix("/a/")
    first_slash = asset_path.index("/")
    vid = asset_path[:first_slash]
    rel = asset_path[first_slash + 1 :]

    raw = await c.get(
        f"/a/{vid}/{rel}",
        params={
            "exp": q["exp"][0],
            "sig": q["sig"][0],
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert raw.status_code == 200
    assert b"data-promptdeck-probe" in raw.content
    assert b"postMessage" in raw.content

    bad = await c.get(
        f"/a/{vid}/{rel}",
        params={
            "exp": q["exp"][0],
            "sig": "0" * 64,
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert bad.status_code == 403


def _sample_zip_bundle() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "index.html",
            b"""<!DOCTYPE html>
<html><head><title>Bundle</title><link rel="stylesheet" href="assets/app.css" /></head>
<body><section><p>Slide A</p></section><section><p>Slide B</p></section></body></html>
""",
        )
        zf.writestr("assets/app.css", b"body { color: green; }")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_zip_bundle_embed_and_asset(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Zip deck"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("site.zip", _sample_zip_bundle(), "application/zip")},
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["storage_kind"] == "zip_bundle"
    assert body["entry_path"] == "index.html"
    assert len(body.get("slides") or []) >= 1

    emb = await c.get(f"/api/v1/presentations/{pid}/embed")
    assert emb.status_code == 200
    iframe_src = emb.json()["iframe_src"]
    parsed = urlparse(iframe_src)
    q = parse_qs(parsed.query)
    asset_path = parsed.path.removeprefix("/a/")
    first_slash = asset_path.index("/")
    vid = asset_path[:first_slash]
    rel = asset_path[first_slash + 1 :]

    html_resp = await c.get(
        f"/a/{vid}/{rel}",
        params={
            "exp": q["exp"][0],
            "sig": q["sig"][0],
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert html_resp.status_code == 200
    assert b"data-promptdeck-probe" in html_resp.content

    css_resp = await c.get(
        f"/a/{vid}/assets/app.css",
        params={
            "exp": q["exp"][0],
            "sig": q["sig"][0],
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert css_resp.status_code == 200
    assert b"green" in css_resp.content


@pytest.mark.asyncio
async def test_upload_zip_rejects_path_traversal(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Bad zip"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", b"<html><body>ok</body></html>")
        zf.writestr("../evil.html", b"no")
    raw = buf.getvalue()

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("bad.zip", raw, "application/zip")},
    )
    assert up.status_code == 400


@pytest.mark.asyncio
async def test_patch_presentation_records_audit(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "A"})
    assert r0.status_code == 201
    pid = uuid.UUID(r0.json()["id"])
    patch = await c.patch(f"/api/v1/presentations/{pid}", json={"title": "B"})
    assert patch.status_code == 200

    async with session_factory()() as session:
        n = (
            await session.execute(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "presentation.updated", AuditLog.target_id == pid),
            )
        ).scalar_one()
    assert int(n) >= 1


@pytest.mark.asyncio
async def test_delete_presentation_records_audit(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Z"})
    assert r0.status_code == 201
    pid = uuid.UUID(r0.json()["id"])
    d = await c.delete(f"/api/v1/presentations/{pid}")
    assert d.status_code == 204

    async with session_factory()() as session:
        n = (
            await session.execute(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "presentation.deleted", AuditLog.target_id == pid),
            )
        ).scalar_one()
    assert int(n) >= 1
