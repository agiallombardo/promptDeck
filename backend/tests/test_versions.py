from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from app.db.models.user import User, UserRole
from app.db.session import session_factory
from app.security.passwords import hash_password
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_html_version(authed_client: AsyncClient, sample_deck_path: Path) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Fixture deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    raw = sample_deck_path.read_bytes()
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("sample_deck.html", raw, "text/html")},
    )
    assert up.status_code == 201
    body = up.json()
    assert body["id"]
    assert len(body.get("slides") or []) >= 1


@pytest.mark.skipif(
    ":memory:" in os.environ.get("DATABASE_URL", ""),
    reason="SQLite :memory: uses a single DB connection; concurrent requests overlap",
)
@pytest.mark.asyncio
async def test_concurrent_uploads_assign_unique_version_numbers(
    authed_client: AsyncClient, sample_deck_path: Path
) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Concurrent deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    raw = sample_deck_path.read_bytes()

    async def do_upload() -> int:
        resp = await c.post(
            f"/api/v1/presentations/{pid}/versions",
            files={"file": ("sample_deck.html", raw, "text/html")},
        )
        assert resp.status_code == 201, resp.text
        return int(resp.json()["version_number"])

    version_numbers = await asyncio.gather(do_upload(), do_upload())
    assert sorted(version_numbers) == [1, 2]


def _html_with_managed_blocks() -> bytes:
    return b"""<!DOCTYPE html>
<html>
  <head>
    <style>.keep-me { color: blue; }</style>
    <style data-promptdeck-managed="code-css">.from-managed { color: red; }</style>
  </head>
  <body>
    <section><h1>Hello</h1></section>
    <script>window.keepMe = true;</script>
    <script data-promptdeck-managed="code-js">window.managed = 1;</script>
  </body>
</html>
"""


def _html_without_managed_blocks() -> bytes:
    return b"""<!DOCTYPE html>
<html>
  <head><title>Plain</title><style>.base { margin: 0; }</style></head>
  <body><section><h1>Plain</h1></section><script>window.base = true;</script></body>
</html>
"""


async def _fetch_current_asset_html(client: AsyncClient, presentation_id: str) -> bytes:
    emb = await client.get(f"/api/v1/presentations/{presentation_id}/embed")
    assert emb.status_code == 200
    iframe_src = emb.json()["iframe_src"]
    parsed = urlparse(iframe_src)
    q = parse_qs(parsed.query)
    asset_path = parsed.path.removeprefix("/a/")
    first_slash = asset_path.index("/")
    vid = asset_path[:first_slash]
    rel = asset_path[first_slash + 1 :]
    html_resp = await client.get(
        f"/a/{vid}/{rel}",
        params={
            "exp": q["exp"][0],
            "sig": q["sig"][0],
            "sub": q["sub"][0],
            "role": q["role"][0],
        },
    )
    assert html_resp.status_code == 200
    return html_resp.content


@pytest.mark.asyncio
async def test_current_code_get_returns_managed_blocks(authed_client: AsyncClient) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Managed code deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", _html_with_managed_blocks(), "text/html")},
    )
    assert up.status_code == 201

    code = await c.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert code.status_code == 200, code.text
    body = code.json()
    assert body["version_id"] == up.json()["id"]
    assert body["css"] == ".from-managed { color: red; }"
    assert body["js"] == "window.managed = 1;"
    assert "data-promptdeck-managed" in body["html"]


@pytest.mark.asyncio
async def test_current_code_get_without_managed_blocks_returns_empty_tabs(
    authed_client: AsyncClient,
) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Plain code deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", _html_without_managed_blocks(), "text/html")},
    )
    assert up.status_code == 201

    code = await c.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert code.status_code == 200, code.text
    body = code.json()
    assert body["version_id"] == up.json()["id"]
    assert body["css"] == ""
    assert body["js"] == ""


@pytest.mark.asyncio
async def test_current_code_save_creates_new_version_and_preserves_non_managed(
    authed_client: AsyncClient,
) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Save code deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", _html_with_managed_blocks(), "text/html")},
    )
    assert up.status_code == 201

    code = await c.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert code.status_code == 200
    base = code.json()
    updated_html = base["html"].replace("<h1>Hello</h1>", "<h1>Hello updated</h1>")
    save = await c.put(
        f"/api/v1/presentations/{pid}/versions/current/code",
        json={
            "base_version_id": base["version_id"],
            "html": updated_html,
            "css": ".new-managed { color: green; }",
            "js": "window.managed = 2;",
        },
    )
    assert save.status_code == 201, save.text
    saved = save.json()
    assert saved["id"] != base["version_id"]
    assert saved["version_number"] == 2

    reloaded = await c.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert reloaded.status_code == 200
    rb = reloaded.json()
    assert rb["version_id"] == saved["id"]
    assert rb["css"] == ".new-managed { color: green; }"
    assert rb["js"] == "window.managed = 2;"
    assert ".keep-me { color: blue; }" in rb["html"]
    assert "window.keepMe = true;" in rb["html"]
    assert "<h1>Hello updated</h1>" in rb["html"]

    rendered = await _fetch_current_asset_html(c, pid)
    assert b".new-managed { color: green; }" in rendered
    assert b"window.managed = 2;" in rendered
    assert b"window.keepMe = true;" in rendered


@pytest.mark.asyncio
async def test_current_code_save_rejects_stale_base_version(authed_client: AsyncClient) -> None:
    c = authed_client
    pres = await c.post("/api/v1/presentations", json={"title": "Conflict code deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    up = await c.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", _html_without_managed_blocks(), "text/html")},
    )
    assert up.status_code == 201

    code = await c.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert code.status_code == 200
    base = code.json()

    first = await c.put(
        f"/api/v1/presentations/{pid}/versions/current/code",
        json={
            "base_version_id": base["version_id"],
            "html": base["html"],
            "css": ".one { color: black; }",
            "js": "",
        },
    )
    assert first.status_code == 201, first.text

    stale = await c.put(
        f"/api/v1/presentations/{pid}/versions/current/code",
        json={
            "base_version_id": base["version_id"],
            "html": base["html"],
            "css": ".two { color: black; }",
            "js": "",
        },
    )
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_current_code_routes_forbid_non_editor(client: AsyncClient) -> None:
    async with session_factory()() as session:
        owner_email = "owner-code@example.com"
        owner_pw = "owner-pass-1"
        outsider_email = "outsider-code@example.com"
        outsider_pw = "outsider-pass-1"
        session.add(
            User(
                email=owner_email,
                display_name="Owner",
                password_hash=hash_password(owner_pw),
                role=UserRole.user,
            )
        )
        session.add(
            User(
                email=outsider_email,
                display_name="Outsider",
                password_hash=hash_password(outsider_pw),
                role=UserRole.user,
            )
        )
        await session.commit()

    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner-code@example.com", "password": "owner-pass-1"},
    )
    assert owner_login.status_code == 200
    client.headers.update({"Authorization": f"Bearer {owner_login.json()['access_token']}"})

    pres = await client.post("/api/v1/presentations", json={"title": "Protected code deck"})
    assert pres.status_code == 201
    pid = pres.json()["id"]
    up = await client.post(
        f"/api/v1/presentations/{pid}/versions",
        files={"file": ("deck.html", _html_without_managed_blocks(), "text/html")},
    )
    assert up.status_code == 201

    outsider_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "outsider-code@example.com", "password": "outsider-pass-1"},
    )
    assert outsider_login.status_code == 200
    client.headers.update({"Authorization": f"Bearer {outsider_login.json()['access_token']}"})

    blocked_get = await client.get(f"/api/v1/presentations/{pid}/versions/current/code")
    assert blocked_get.status_code == 403
    blocked_put = await client.put(
        f"/api/v1/presentations/{pid}/versions/current/code",
        json={
            "base_version_id": up.json()["id"],
            "html": "<!DOCTYPE html><html><body><section>x</section></body></html>",
            "css": "",
            "js": "",
        },
    )
    assert blocked_put.status_code == 403
