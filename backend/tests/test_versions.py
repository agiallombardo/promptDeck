from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
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
