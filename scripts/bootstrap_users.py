#!/usr/bin/env python3
"""Create initial local users (admin + optional demo user)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "changeme123")
os.environ.setdefault("BOOTSTRAP_USER_EMAIL", "user@example.com")
os.environ.setdefault("BOOTSTRAP_USER_PASSWORD", "changeme123")


def _truthy_env(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    return raw.strip().lower() in ("1", "true", "yes", "on")


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

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

    demo_flag = _truthy_env("BOOTSTRAP_DEMO_USERS")
    include_demo_user = demo_flag if demo_flag is not None else (settings.environment == "development")

    admin_email = os.environ["BOOTSTRAP_ADMIN_EMAIL"].lower().strip()
    admin_password = os.environ["BOOTSTRAP_ADMIN_PASSWORD"]
    demo_user_email = os.environ["BOOTSTRAP_USER_EMAIL"].lower().strip()
    demo_user_password = os.environ["BOOTSTRAP_USER_PASSWORD"]

    log.info(
        "script.bootstrap_users.start",
        admin_email=admin_email,
        include_demo_user=include_demo_user,
        environment=settings.environment,
    )

    async def ensure_user(
        session: AsyncSession,
        *,
        email: str,
        password: str,
        role: UserRole,
        display_name: str,
    ) -> None:
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            log.info("script.bootstrap_users.skip_existing", email=email)
            print(f"bootstrap_users: user already exists: {email}")
            return
        session.add(
            User(
                email=email,
                display_name=display_name,
                password_hash=hash_password(password),
                role=role,
            )
        )
        await session.commit()
        log.info("script.bootstrap_users.created", email=email, role=role.value)
        print(f"bootstrap_users: created {role.value} {email}")

    async with session_factory()() as session:
        await ensure_user(
            session,
            email=admin_email,
            password=admin_password,
            role=UserRole.admin,
            display_name="Administrator",
        )
        if include_demo_user:
            if demo_user_email == admin_email:
                log.info(
                    "script.bootstrap_users.skip_demo_user",
                    reason="demo user email matches admin",
                )
                print("bootstrap_users: skipped demo user (same email as admin)")
            else:
                await ensure_user(
                    session,
                    email=demo_user_email,
                    password=demo_user_password,
                    role=UserRole.user,
                    display_name="Demo user",
                )
        else:
            log.info(
                "script.bootstrap_users.skip_demo_user",
                reason="BOOTSTRAP_DEMO_USERS off / non-development",
            )
            print("bootstrap_users: skipped demo user (set BOOTSTRAP_DEMO_USERS=1 to force)")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
