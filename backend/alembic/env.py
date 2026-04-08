from __future__ import annotations

import asyncio

from alembic import context
from app.config import get_settings
from app.db.base import Base
from app.db.models import AppLog, User  # noqa: F401
from app.db.models.comment_thread import Comment, CommentThread  # noqa: F401
from app.db.models.export_job import ExportJob  # noqa: F401
from app.db.models.presentation import Presentation, PresentationVersion, Slide  # noqa: F401
from app.db.models.share_link import ShareLink  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

target_metadata = Base.metadata


def get_url() -> str:
    url = get_settings().database_url
    if url.startswith("postgresql+asyncpg"):
        return url
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_async_migrations() -> None:
    asyncio.run(run_migrations_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async_migrations()
