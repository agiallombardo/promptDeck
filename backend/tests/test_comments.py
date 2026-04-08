from __future__ import annotations

import uuid

import pytest
from app.config import get_settings
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient

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
                email="comments@example.com",
                display_name="Comments",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.editor,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "comments@example.com", "password": "secret-pass-1"},
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
async def test_threads_create_list_reply_resolve_delete(editor_client) -> None:
    c, _transport = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Comment deck"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201
    version_id = up.json()["id"]

    empty = await c.get(f"/api/v1/presentations/{pid}/threads")
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    create = await c.post(
        f"/api/v1/presentations/{pid}/threads",
        json={
            "version_id": version_id,
            "slide_index": 0,
            "anchor_x": 0.5,
            "anchor_y": 0.5,
            "first_comment": "hello",
        },
    )
    assert create.status_code == 201, create.text
    tid = create.json()["id"]
    assert len(create.json()["comments"]) == 1

    listed = await c.get(f"/api/v1/presentations/{pid}/threads")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    cid = listed.json()["items"][0]["comments"][0]["id"]

    rep = await c.post(
        f"/api/v1/threads/{tid}/comments",
        json={"body": "second"},
    )
    assert rep.status_code == 201

    patch = await c.patch(
        f"/api/v1/threads/{tid}",
        json={"status": "resolved"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "resolved"

    delete = await c.delete(f"/api/v1/comments/{cid}")
    assert delete.status_code == 204

    after = await c.get(f"/api/v1/presentations/{pid}/threads")
    assert after.status_code == 200
    comments = after.json()["items"][0]["comments"]
    assert len(comments) == 1
    assert comments[0]["body"] == "second"


@pytest.mark.asyncio
async def test_viewer_cannot_create_thread(tmp_path, monkeypatch):
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

    oid = uuid.uuid4()
    async with session_factory()() as session:
        session.add(
            User(
                id=oid,
                email="viewer@example.com",
                display_name="View",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.viewer,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "secret-pass-1"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        ac.headers.update({"Authorization": f"Bearer {token}"})

        pres = await ac.post("/api/v1/presentations", json={"title": "V"})
        assert pres.status_code == 201
        pid = pres.json()["id"]

        up = await ac.post(
            f"/api/v1/presentations/{pid}/versions",
            files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
        )
        assert up.status_code == 201
        version_id = up.json()["id"]

        blocked = await ac.post(
            f"/api/v1/presentations/{pid}/threads",
            json={
                "version_id": version_id,
                "slide_index": 0,
                "anchor_x": 0.1,
                "anchor_y": 0.2,
                "first_comment": "nope",
            },
        )
        assert blocked.status_code == 403

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_share_commenter_can_post_thread_and_reply(editor_client) -> None:
    c, transport = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Share comments"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201
    version_id = up.json()["id"]

    sh = await c.post(
        f"/api/v1/presentations/{pid}/shares",
        json={"role": "commenter"},
    )
    assert sh.status_code == 201
    secret = sh.json()["token"]

    async with AsyncClient(transport=transport, base_url="http://test") as exc:
        ex = await exc.post("/api/v1/shares/exchange", json={"token": secret})
    assert ex.status_code == 200
    share_token = ex.json()["access_token"]

    async with AsyncClient(transport=transport, base_url="http://test") as share_client:
        share_client.headers.update({"Authorization": f"Bearer {share_token}"})
        create = await share_client.post(
            f"/api/v1/presentations/{pid}/threads",
            json={
                "version_id": version_id,
                "slide_index": 0,
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "first_comment": "from share",
            },
        )
        assert create.status_code == 201, create.text
        tid = create.json()["id"]
        assert create.json()["created_by"] is None
        assert create.json()["comments"][0]["author_id"] is None
        assert create.json()["comments"][0]["author_display_name"] == "Shared commenter"

        rep = await share_client.post(
            f"/api/v1/threads/{tid}/comments",
            json={"body": "reply from share"},
        )
        assert rep.status_code == 201
        assert rep.json()["author_display_name"] == "Shared commenter"
