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
<html><head><title>T</title></head><body><section><p>One</p></section></body></html>
"""

_EDITED_HTML = """<!DOCTYPE html>
<html><head><title>E</title></head><body><section><p>Edited</p></section></body></html>"""


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
                email="sartifact@example.com",
                display_name="SA",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.user,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "sartifact@example.com", "password": "secret-pass-1"},
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
async def test_source_artifact_upload_requires_intent(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "Src"})
    assert r0.status_code == 201
    pid = r0.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    assert up.status_code == 201

    bad = await c.post(
        f"/api/v1/presentations/{pid}/source-artifacts",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 422

    bad2 = await c.post(
        f"/api/v1/presentations/{pid}/source-artifacts",
        data={"intent": "nope"},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert bad2.status_code == 400

    ok = await c.post(
        f"/api/v1/presentations/{pid}/source-artifacts",
        data={"intent": "inspire"},
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["intent"] == "inspire"
    assert body["original_filename"] == "note.txt"


@pytest.mark.asyncio
async def test_source_artifact_list_patch_delete(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "LPD"})
    pid = r0.json()["id"]
    await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    up = await c.post(
        f"/api/v1/presentations/{pid}/source-artifacts",
        data={"intent": "embed"},
        files={"file": ("x.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    aid = up.json()["id"]

    lst = await c.get(f"/api/v1/presentations/{pid}/source-artifacts")
    assert lst.status_code == 200
    assert len(lst.json()["items"]) == 1

    pat = await c.patch(
        f"/api/v1/presentations/{pid}/source-artifacts/{aid}",
        json={"intent": "inspire"},
    )
    assert pat.status_code == 200
    assert pat.json()["intent"] == "inspire"

    de = await c.delete(f"/api/v1/presentations/{pid}/source-artifacts/{aid}")
    assert de.status_code == 204

    lst2 = await c.get(f"/api/v1/presentations/{pid}/source-artifacts")
    assert lst2.json()["items"] == []


@pytest.mark.asyncio
async def test_deck_prompt_job_rejects_foreign_artifact(editor_client: AsyncClient) -> None:
    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "A"})
    pid_a = r0.json()["id"]
    r1 = await c.post("/api/v1/presentations", json={"title": "B"})
    pid_b = r1.json()["id"]
    for pid in (pid_a, pid_b):
        await c.post(
            f"/api/v1/presentations/{pid}/versions",
            files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
        )
    up = await c.post(
        f"/api/v1/presentations/{pid_a}/source-artifacts",
        data={"intent": "inspire"},
        files={"file": ("n.txt", b"x", "text/plain")},
    )
    aid = up.json()["id"]

    job = await c.post(
        f"/api/v1/presentations/{pid_b}/deck-prompt-jobs",
        json={"prompt": "x", "source_artifact_ids": [aid]},
    )
    assert job.status_code == 400


@pytest.mark.asyncio
async def test_deck_prompt_job_sends_artifact_context(
    editor_client: AsyncClient,
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    async def _fake_complete(*, user_message: str, **_kwargs: object) -> object:
        from app.services.deck_llm_completion import DeckLlmCompletionResult

        captured["user_message"] = user_message
        return DeckLlmCompletionResult(text=_EDITED_HTML)

    monkeypatch.setattr(
        "app.jobs.deck_prompt_runner.complete_deck_html_edit",
        _fake_complete,
    )

    c = editor_client
    r0 = await c.post("/api/v1/presentations", json={"title": "LLM ctx"})
    pid = r0.json()["id"]
    await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", SAMPLE_HTML, "text/html")},
    )
    up = await c.post(
        f"/api/v1/presentations/{pid}/source-artifacts",
        data={"intent": "inspire"},
        files={"file": ("brief.txt", b"Use tone: friendly", "text/plain")},
    )
    aid = up.json()["id"]

    job = await c.post(
        f"/api/v1/presentations/{pid}/deck-prompt-jobs",
        json={"prompt": "Shorten", "source_artifact_ids": [aid]},
    )
    assert job.status_code == 202
    jid = job.json()["id"]

    for _ in range(80):
        g = await c.get(f"/api/v1/deck-prompt-jobs/{jid}")
        if g.json()["status"] in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)

    assert "SOURCE_ARTIFACTS_START" in captured.get("user_message", "")
    assert "brief.txt" in captured["user_message"]
    assert "intent=inspire" in captured["user_message"]
    assert "Presentation title: LLM ctx" in captured["user_message"]
    assert "Presentation type: deck" in captured["user_message"]
