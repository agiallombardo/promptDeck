#!/usr/bin/env python3
"""Seed application data (not users). User accounts: see scripts/bootstrap_users.py."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))


async def main() -> None:
    from app.logging_channels import LogChannel, channel_logger
    from app.logging_conf import configure_logging

    configure_logging()
    log = channel_logger(LogChannel.script)
    log.info("script.seed.noop", detail="no application seed data configured")
    print("seed: no application data to insert (users: scripts/bootstrap_users.py)")


if __name__ == "__main__":
    asyncio.run(main())
