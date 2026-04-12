"""Settings and secret material behavior."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield None
    get_settings.cache_clear()


def test_asset_signing_secret_falls_back_to_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "j" * 32)
    monkeypatch.delenv("ASSET_SIGNING_KEY", raising=False)
    s = Settings()
    assert s.asset_signing_key is None
    assert s.asset_signing_secret_bytes() == b"j" * 32


def test_asset_signing_secret_uses_dedicated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "j" * 32)
    monkeypatch.setenv("ASSET_SIGNING_KEY", "a" * 32)
    s = Settings()
    assert s.asset_signing_secret_bytes() == b"a" * 32
