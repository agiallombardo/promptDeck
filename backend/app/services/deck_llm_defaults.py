"""Default deck-edit model ids per provider.

These are the current "normal" tier flagships (not Pro / Opus). Bump the constants when
vendors ship new defaults; operators can override without code changes via env (see Settings)
or a single DECK_LLM_MODEL for all providers.
"""

from __future__ import annotations

from typing import Literal

from app.config import Settings

DeckLlmKind = Literal["litellm", "openai", "claude"]

# OpenAI: general `gpt-5.4` alias (not `gpt-5.4-pro`).
DECK_LLM_DEFAULT_OPENAI = "gpt-5.4"

# Anthropic: Sonnet tier (not Opus).
DECK_LLM_DEFAULT_ANTHROPIC = "claude-sonnet-4-6"

# LiteLLM: route to Claude Sonnet by default (model string is whatever the proxy accepts).
DECK_LLM_DEFAULT_LITELLM = "claude-sonnet-4-6"


def effective_deck_llm_model(settings: Settings, kind: DeckLlmKind) -> str:
    """Resolve model id: global override, then per-provider env, then baked-in default."""
    global_override = (settings.deck_llm_model or "").strip()
    if global_override:
        return global_override

    if kind == "openai":
        v = (settings.deck_llm_model_openai or "").strip()
        return v or DECK_LLM_DEFAULT_OPENAI
    if kind == "claude":
        v = (settings.deck_llm_model_anthropic or "").strip()
        return v or DECK_LLM_DEFAULT_ANTHROPIC
    v = (settings.deck_llm_model_litellm or "").strip()
    return v or DECK_LLM_DEFAULT_LITELLM
