#!/usr/bin/env python3
"""Golden-path smoke: in-process ASGI health check with SQLite + schema (no running server)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


async def _run() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.db.base import Base
    from app.db.session import dispose_engine, get_engine
    from app.logging_channels import LogChannel, channel_logger
    from app.logging_conf import configure_logging
    from app.main import app

    configure_logging()
    script_log = channel_logger(LogChannel.script)
    script_log.info("script.smoke.start")

    get_settings.cache_clear()
    await dispose_engine()
    get_settings.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        if r.status_code != 200 or r.json().get("status") != "ok":
            raise SystemExit(f"FAIL: unexpected health {r.status_code} {r.text}")

    script_log.info("script.smoke.pass")
    await dispose_engine()
    get_settings.cache_clear()


def main() -> None:
    asyncio.run(_run())
    print("PASS")


if __name__ == "__main__":
    main()
