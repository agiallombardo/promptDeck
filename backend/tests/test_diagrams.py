from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from urllib.parse import parse_qs, urlparse

import pytest
from app.config import get_settings
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from app.services.deck_llm_completion import DeckLlmCompletionResult
from app.services.diagram_import import DiagramImportResult
from httpx import ASGITransport, AsyncClient

_DIAGRAM_JSON = """{
  "nodes": [
    {"id": "n1", "type": "input", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
    {"id": "n2", "type": "default", "position": {"x": 320, "y": 0}, "data": {"label": "Process"}}
  ],
  "edges": [{"id": "e1", "source": "n1", "target": "n2", "type": "smoothstep"}],
  "viewport": {"x": 0, "y": 0, "zoom": 1}
}"""

_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c\xf8\xff\xff?\x00\x05\xfe"
    b"\x02\xfeA\xc2w\x9b\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
                email="diagram@example.com",
                display_name="Diagram User",
                password_hash=hash_password("secret-pass-1"),
                role=UserRole.user,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post(
            "/api/v1/auth/login",
            json={"email": "diagram@example.com", "password": "secret-pass-1"},
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
async def test_create_and_save_diagram(editor_client: AsyncClient) -> None:
    c = editor_client
    created = await c.post(
        "/api/v1/presentations",
        json={"title": "Architecture", "kind": "diagram"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["kind"] == "diagram"
    assert body["current_version_id"] is not None
    pid = body["id"]

    g = await c.get(f"/api/v1/presentations/{pid}/diagram")
    assert g.status_code == 200
    assert g.json()["document"]["nodes"] == []

    put = await c.put(
        f"/api/v1/presentations/{pid}/diagram",
        json={
            "document": {
                "nodes": [
                    {
                        "id": "n1",
                        "position": {"x": 10, "y": 20},
                        "data": {"label": "Gateway", "icon": "gateway"},
                    }
                ],
                "edges": [],
            }
        },
    )
    assert put.status_code == 200, put.text
    saved = put.json()
    assert saved["document"]["nodes"][0]["id"] == "n1"
    assert saved["document"]["nodes"][0]["data"]["icon"] == "gateway"
    assert "viewport" in saved["document"]

    thread = await c.post(
        f"/api/v1/presentations/{pid}/threads",
        json={
            "version_id": saved["version_id"],
            "slide_index": 0,
            "anchor_x": 0.5,
            "anchor_y": 0.5,
            "target_kind": "node",
            "target_id": "n1",
            "first_comment": "Looks good",
        },
    )
    assert thread.status_code == 201, thread.text
    assert thread.json()["target_kind"] == "node"
    assert thread.json()["target_id"] == "n1"

    bad = await c.post(
        f"/api/v1/presentations/{pid}/threads",
        json={
            "version_id": saved["version_id"],
            "slide_index": 0,
            "anchor_x": 0.4,
            "anchor_y": 0.4,
            "target_kind": "node",
            "target_id": "missing",
            "first_comment": "x",
        },
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_generate_diagram_from_prompt_happy_path(
    editor_client: AsyncClient, monkeypatch
) -> None:
    captured: dict[str, str] = {}

    async def _fake_complete(*, user_message: str, **_kwargs: object) -> DeckLlmCompletionResult:
        captured["user_message"] = user_message
        return DeckLlmCompletionResult(
            text=_DIAGRAM_JSON,
            prompt_tokens=9,
            completion_tokens=17,
            total_tokens=26,
        )

    monkeypatch.setattr("app.jobs.deck_prompt_runner.complete_deck_html_edit", _fake_complete)

    c = editor_client
    r = await c.post(
        "/api/v1/presentations/generate-diagram-from-prompt",
        json={"title": "Generated Diagram", "prompt": "Create a data flow"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["presentation"]["kind"] == "diagram"
    jid = body["job"]["id"]
    assert body["job"]["job_type"] == "diagram_generate"
    assert body["job"]["is_generation"] is True

    status = "queued"
    poll_body: dict = {}
    for _ in range(80):
        g = await c.get(f"/api/v1/deck-prompt-jobs/{jid}")
        assert g.status_code == 200
        poll_body = g.json()
        status = poll_body["status"]
        if status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)

    assert status == "succeeded", poll_body.get("error")
    assert poll_body.get("result_version_id")
    assert poll_body.get("job_type") == "diagram_generate"
    assert "Presentation title: Generated Diagram" in captured.get("user_message", "")
    assert "Presentation type: diagram" in captured["user_message"]


@pytest.mark.asyncio
async def test_diagram_upload_imports_pdf_image_and_zip(
    editor_client: AsyncClient, monkeypatch
) -> None:
    async def _fake_convert(**_kwargs: object) -> DiagramImportResult:
        return DiagramImportResult(
            document_text=_DIAGRAM_JSON,
            usage=DeckLlmCompletionResult(text=_DIAGRAM_JSON),
        )

    monkeypatch.setattr("app.routers.versions.convert_uploaded_source_to_diagram", _fake_convert)

    c = editor_client
    created = await c.post("/api/v1/presentations", json={"title": "Imports", "kind": "diagram"})
    assert created.status_code == 201
    pid = created.json()["id"]

    pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    r_pdf = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("import.pdf", pdf_bytes, "application/pdf")},
    )
    assert r_pdf.status_code == 201, r_pdf.text
    assert r_pdf.json()["storage_kind"] == "xyflow_json"

    r_img = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("net.png", _TINY_PNG, "image/png")},
    )
    assert r_img.status_code == 201, r_img.text
    assert r_img.json()["storage_kind"] == "xyflow_json"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("diagram.drawio", "<mxfile><diagram>sample</diagram></mxfile>")
        zf.writestr("meta/readme.txt", "network topology")
    r_zip = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("src.zip", buf.getvalue(), "application/zip")},
    )
    assert r_zip.status_code == 201, r_zip.text
    assert r_zip.json()["storage_kind"] == "xyflow_json"


@pytest.mark.asyncio
async def test_diagram_export_single_html(editor_client: AsyncClient) -> None:
    c = editor_client
    created = await c.post("/api/v1/presentations", json={"title": "Export me", "kind": "diagram"})
    assert created.status_code == 201
    pid = created.json()["id"]
    put = await c.put(
        f"/api/v1/presentations/{pid}/diagram",
        json={"document": json.loads(_DIAGRAM_JSON)},
    )
    assert put.status_code == 200

    j = await c.post(
        f"/api/v1/presentations/{pid}/exports",
        json={"format": "single_html"},
    )
    assert j.status_code == 202, j.text
    jid = j.json()["id"]
    for _ in range(120):
        r = await c.get(f"/api/v1/exports/{jid}")
        assert r.status_code == 200
        if r.json()["status"] == "succeeded":
            dl = await c.get(f"/api/v1/exports/{jid}/file")
            assert dl.status_code == 200
            assert dl.headers.get("content-type", "").startswith("text/html")
            assert b"<html" in dl.content
            return
        if r.json()["status"] == "failed":
            raise AssertionError(r.json().get("error") or "export failed")
        await asyncio.sleep(0.05)
    raise AssertionError("html export did not complete")


@pytest.mark.asyncio
async def test_diagram_thumbnail_endpoint_and_asset(editor_client: AsyncClient) -> None:
    c = editor_client
    created = await c.post("/api/v1/presentations", json={"title": "Thumb", "kind": "diagram"})
    assert created.status_code == 201
    pid = created.json()["id"]

    thumb = await c.get(f"/api/v1/presentations/{pid}/diagram/thumbnail")
    assert thumb.status_code == 200, thumb.text
    body = thumb.json()
    assert body["png_src"]
    parsed = urlparse(body["png_src"])
    path = parsed.path.removeprefix("/a/")
    slash = path.index("/")
    vid = path[:slash]
    rel = path[slash + 1 :]
    q = parse_qs(parsed.query)
    g = await c.get(
        f"/a/{vid}/{rel}",
        params={
            "exp": q["exp"][0],
            "sig": q["sig"][0],
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert g.status_code == 200
    assert g.headers.get("content-type", "").startswith("image/png")
