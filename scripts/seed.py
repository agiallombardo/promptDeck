#!/usr/bin/env python3
"""Create initial admin user (requires DATABASE_URL and applied migrations / schema)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "changeme123")


async def main() -> None:
    from sqlalchemy import select

    from app.config import get_settings
    from app.db.models.user import User, UserRole
    from app.db.session import dispose_engine, session_factory
    from app.logging_channels import LogChannel, channel_logger
    from app.logging_conf import configure_logging
    from app.security.passwords import hash_password

    configure_logging()
    log = channel_logger(LogChannel.script)

    get_settings.cache_clear()
    settings = get_settings()
    email = os.environ["SEED_ADMIN_EMAIL"].lower().strip()
    password = os.environ["SEED_ADMIN_PASSWORD"]

    log.info("script.seed.start", email=email)

    async with session_factory()() as session:
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            log.info("script.seed.skip_existing", email=email)
            print(f"seed: user already exists: {email}")
            await dispose_engine()
            return

        session.add(
            User(
                email=email,
                display_name="Administrator",
                password_hash=hash_password(password),
                role=UserRole.admin,
            )
        )
        await session.commit()
        log.info("script.seed.created", email=email, environment=settings.environment)
        print(f"seed: created admin {email} (environment={settings.environment})")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
