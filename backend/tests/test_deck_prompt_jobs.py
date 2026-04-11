from __future__ import annotations

import asyncio
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

_EDITED_HTML = """<!DOCTYPE html>
<html><head><title>E</title></head>
<body><section><p>Edited</p></section></body></html>"""


@pytest.fixture
async def editor_client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("LITELLM_API_BASE", "http://llm.test.invalid/v1")
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
                email="deckprompt@example.com",
                display_name="DP",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.user,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "deckprompt@example.com", "password": "secret-pass-1"},
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
async def test_deck_prompt_job_happy_path(editor_client: AsyncClient, monkeypatch) -> None:
    async def _fake_complete(**_kwargs: object) -> str:
        return _EDITED_HTML

    monkeypatch.setattr(
        "app.jobs.deck_prompt_runner.complete_deck_html_edit",
        _fake_complete,
    )

    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "AI deck"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201, up.text

    job = await c.post(
        f"/api/v1/presentations/{pid}/deck-prompt-jobs",
        json={"prompt": "Make it shorter"},
    )
    assert job.status_code == 202, job.text
    jid = job.json()["id"]
    assert job.json()["status"] in ("queued", "running", "succeeded")

    status = "queued"
    err = None
    for _ in range(80):
        g = await c.get(f"/api/v1/deck-prompt-jobs/{jid}")
        assert g.status_code == 200
        body = g.json()
        status = body["status"]
        err = body.get("error")
        if status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)

    assert status == "succeeded", err
    assert body.get("result_version_id")
    assert body.get("progress") == 100

    pres = await c.get(f"/api/v1/presentations/{pid}")
    assert pres.status_code == 200
    assert pres.json()["current_version_id"] == body["result_version_id"]


@pytest.mark.asyncio
async def test_deck_prompt_job_requires_version(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Empty"})
    assert r0.status_code == 201
    pid = r0.json()["id"]

    job = await c.post(
        f"/api/v1/presentations/{pid}/deck-prompt-jobs",
        json={"prompt": "x"},
    )
    assert job.status_code == 400


@pytest.mark.asyncio
async def test_deck_prompt_job_fails_if_llm_unconfigured(
    editor_client: AsyncClient,
    monkeypatch,
) -> None:
    monkeypatch.delenv("LITELLM_API_BASE", raising=False)
    get_settings.cache_clear()

    async def _fake_complete(**_kwargs: object) -> str:
        return _EDITED_HTML

    monkeypatch.setattr(
        "app.jobs.deck_prompt_runner.complete_deck_html_edit",
        _fake_complete,
    )

    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "No LLM"})
    assert r0.status_code == 201
    pid = r0.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    job = await c.post(
        f"/api/v1/presentations/{pid}/deck-prompt-jobs",
        json={"prompt": "go"},
    )
    assert job.status_code == 202
    jid = job.json()["id"]

    status = "queued"
    err = None
    for _ in range(80):
        g = await c.get(f"/api/v1/deck-prompt-jobs/{jid}")
        body = g.json()
        status = body["status"]
        err = body.get("error")
        if status == "failed":
            break
        await asyncio.sleep(0.05)

    assert status == "failed"
    assert err and "not configured" in err.lower()
