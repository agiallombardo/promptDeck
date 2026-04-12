from collections.abc import AsyncIterator

from app.config import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        if ":memory:" in database_url:
            return {"pool_pre_ping": False}
        return {"pool_pre_ping": False, "poolclass": NullPool}
    return {"pool_pre_ping": True}


def _ensure_factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory
    if _session_factory is not None:
        return _session_factory
    settings = get_settings()
    _engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _session_factory


def get_engine() -> AsyncEngine:
    _ensure_factory()
    assert _engine is not None
    return _engine


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = _ensure_factory()
    async with factory() as session:
        yield session


def session_factory() -> async_sessionmaker[AsyncSession]:
    return _ensure_factory()
