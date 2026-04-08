#!/usr/bin/env python3
"""In-process ASGI smoke: schema, health, auth, upload, comment thread (no external server)."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


async def _run() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.db.base import Base
    from app.db.models.user import User, UserRole
    from app.db.session import dispose_engine, get_engine, session_factory
    from app.logging_channels import LogChannel, channel_logger
    from app.logging_conf import configure_logging
    from app.main import app
    from app.security.passwords import hash_password

    configure_logging()
    script_log = channel_logger(LogChannel.script)
    script_log.info("script.smoke.start")

    get_settings.cache_clear()
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
                email="smoke@example.com",
                display_name="Smoke",
                password_hash=hash_password("smoke-pass-1"),
                role=UserRole.editor,
            )
        )
        await session.commit()

    sample = _BACKEND / "tests" / "fixtures" / "sample_deck.html"
    if not sample.is_file():
        raise SystemExit(f"FAIL: missing {sample}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        if r.status_code != 200 or r.json().get("status") != "ok":
            raise SystemExit(f"FAIL: unexpected health {r.status_code} {r.text}")

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "smoke@example.com", "password": "smoke-pass-1"},
        )
        if login.status_code != 200:
            raise SystemExit(f"FAIL: login {login.status_code} {login.text}")
        token = login.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})

        pres = await client.post("/api/v1/presentations", json={"title": "Smoke deck"})
        if pres.status_code != 201:
            raise SystemExit(f"FAIL: create presentation {pres.status_code}")
        pid = pres.json()["id"]

        up = await client.post(
            f"/api/v1/presentations/{pid}/versions",
            files={"file": ("sample_deck.html", sample.read_bytes(), "text/html")},
        )
        if up.status_code != 201:
            raise SystemExit(f"FAIL: upload {up.status_code} {up.text}")
        version_id = up.json()["id"]

        th = await client.post(
            f"/api/v1/presentations/{pid}/threads",
            json={
                "version_id": version_id,
                "slide_index": 0,
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "first_comment": "smoke thread",
            },
        )
        if th.status_code != 201:
            raise SystemExit(f"FAIL: thread create {th.status_code} {th.text}")

        listed = await client.get(f"/api/v1/presentations/{pid}/threads")
        if listed.status_code != 200:
            raise SystemExit(f"FAIL: list threads {listed.status_code}")
        items = listed.json().get("items") or []
        if len(items) != 1:
            raise SystemExit(f"FAIL: expected 1 thread, got {len(items)}")

    script_log.info("script.smoke.pass")
    await dispose_engine()
    get_settings.cache_clear()


def main() -> None:
    asyncio.run(_run())
    print("PASS")


if __name__ == "__main__":
    main()
