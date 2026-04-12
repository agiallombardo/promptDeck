"""Defaults and env resolution for deck LLM model ids."""

from __future__ import annotations

from app.config import Settings
from app.services.deck_llm_defaults import (
    DECK_LLM_DEFAULT_ANTHROPIC,
    DECK_LLM_DEFAULT_LITELLM,
    DECK_LLM_DEFAULT_OPENAI,
    effective_deck_llm_model,
)
from pydantic_settings import SettingsConfigDict


class _TestSettings(Settings):
    """Avoid loading repo `.env` during unit tests."""

    model_config = SettingsConfigDict(env_file=None, populate_by_name=True)


def test_effective_model_per_provider_defaults() -> None:
    s = _TestSettings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="x" * 32,
        deck_llm_model=None,
        deck_llm_model_openai=None,
        deck_llm_model_anthropic=None,
        deck_llm_model_litellm=None,
    )
    assert effective_deck_llm_model(s, "openai") == DECK_LLM_DEFAULT_OPENAI
    assert effective_deck_llm_model(s, "claude") == DECK_LLM_DEFAULT_ANTHROPIC
    assert effective_deck_llm_model(s, "litellm") == DECK_LLM_DEFAULT_LITELLM
    assert DECK_LLM_DEFAULT_OPENAI == "gpt-5.4"
    assert DECK_LLM_DEFAULT_ANTHROPIC == "claude-sonnet-4-6"
    assert DECK_LLM_DEFAULT_LITELLM == "claude-sonnet-4-6"


def test_global_deck_llm_model_overrides_all() -> None:
    s = _TestSettings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="x" * 32,
        deck_llm_model="custom-model",
    )
    assert effective_deck_llm_model(s, "openai") == "custom-model"
    assert effective_deck_llm_model(s, "claude") == "custom-model"
    assert effective_deck_llm_model(s, "litellm") == "custom-model"


def test_per_provider_env_overrides() -> None:
    s = _TestSettings(
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret_key="x" * 32,
        deck_llm_model=None,
        deck_llm_model_openai="o-mini",
        deck_llm_model_anthropic="claude-other",
        deck_llm_model_litellm="litellm-route",
    )
    assert effective_deck_llm_model(s, "openai") == "o-mini"
    assert effective_deck_llm_model(s, "claude") == "claude-other"
    assert effective_deck_llm_model(s, "litellm") == "litellm-route"
