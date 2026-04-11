import os
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from app.db.models.user import User, UserRole
from app.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOCAL_PASSWORD_AUTH_ENABLED", "true")

from app.config import get_settings

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield None
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.db.base import Base
    from app.db.session import dispose_engine, get_engine
    from app.main import app

    await dispose_engine()
    get_settings.cache_clear()

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    get_settings.cache_clear()


@pytest.fixture
def sample_deck_path() -> Path:
    path = Path(__file__).resolve().parent / "fixtures" / "sample_deck.html"
    assert path.is_file(), f"missing fixture {path}"
    return path


@pytest_asyncio.fixture
async def authed_client(client: AsyncClient):
    from app.db.session import session_factory

    async with session_factory()() as session:
        session.add(
            User(
                id=uuid.uuid4(),
                email="authed-fixture@example.com",
                display_name="Authed fixture",
                password_hash=hash_password("fixture-pw-1"),
                role=UserRole.user,
            )
        )
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "authed-fixture@example.com", "password": "fixture-pw-1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
