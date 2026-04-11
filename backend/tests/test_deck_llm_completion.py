"""Unit tests for OpenAI-shaped completion parsing."""

from __future__ import annotations

import httpx
import pytest
from app.services.deck_llm_completion import complete_deck_html_edit


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self.status_code = 200
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _FakeClient:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def post(self, *_a: object, **_k: object) -> _FakeResponse:
        return _FakeResponse(self._payload)


def _patch_client(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kw: _FakeClient(payload))


@pytest.mark.asyncio
async def test_complete_deck_rejects_non_object_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, [])
    with pytest.raises(ValueError, match="JSON object"):
        await complete_deck_html_edit(
            api_base="http://example.invalid/v1",
            api_key=None,
            model="m",
            system_prompt="sys",
            user_message="user",
        )


@pytest.mark.asyncio
async def test_complete_deck_rejects_non_list_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, {"choices": {}})
    with pytest.raises(ValueError, match="missing choices"):
        await complete_deck_html_edit(
            api_base="http://example.invalid/v1",
            api_key=None,
            model="m",
            system_prompt="sys",
            user_message="user",
        )


@pytest.mark.asyncio
async def test_complete_deck_rejects_non_dict_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, {"choices": ["bad"]})
    with pytest.raises(ValueError, match="choice malformed"):
        await complete_deck_html_edit(
            api_base="http://example.invalid/v1",
            api_key=None,
            model="m",
            system_prompt="sys",
            user_message="user",
        )


@pytest.mark.asyncio
async def test_complete_deck_rejects_non_dict_message(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch, {"choices": [{"message": "nope"}]})
    with pytest.raises(ValueError, match="message malformed"):
        await complete_deck_html_edit(
            api_base="http://example.invalid/v1",
            api_key=None,
            model="m",
            system_prompt="sys",
            user_message="user",
        )


@pytest.mark.asyncio
async def test_complete_deck_happy_path_with_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(
        monkeypatch,
        {
            "choices": [
                {"message": {"content": "<!DOCTYPE html><html><body>x</body></html>"}},
            ],
            "usage": {"prompt_tokens": 4, "completion_tokens": 5, "total_tokens": 9},
        },
    )
    out = await complete_deck_html_edit(
        api_base="http://example.invalid/v1",
        api_key="k",
        model="m",
        system_prompt="sys",
        user_message="user",
    )
    assert "<html" in out.text.lower()
    assert out.prompt_tokens == 4
    assert out.completion_tokens == 5
    assert out.total_tokens == 9
