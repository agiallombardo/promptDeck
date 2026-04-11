"""OpenAI-compatible chat completion for deck HTML editing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

_MAX_COMPLETION_CHARS = 512_000


@dataclass(frozen=True, slots=True)
class DeckLlmCompletionResult:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def _usage_int(raw: object) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return None


def _parse_usage(data: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None, None, None
    return (
        _usage_int(usage.get("prompt_tokens")),
        _usage_int(usage.get("completion_tokens")),
        _usage_int(usage.get("total_tokens")),
    )


def strip_markdown_fenced_html(text: str) -> str:
    s = text.strip()
    fence = re.match(r"^```(?:html|HTML)?\s*\n?", s)
    if fence:
        s = s[fence.end() :]
    if s.endswith("```"):
        s = s[:-3].rstrip()
    return s.strip()


async def complete_deck_html_edit(
    *,
    api_base: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    """Call POST {api_base}/chat/completions; return stripped assistant text and token usage."""
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            detail = r.text[:2000]
            raise ValueError(f"LLM request failed ({r.status_code}): {detail}")
        data = r.json()
    if not isinstance(data, dict):
        raise ValueError("LLM response was not a JSON object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("LLM response choice malformed")
    msg = first.get("message")
    if msg is None:
        msg = {}
    elif not isinstance(msg, dict):
        raise ValueError("LLM response message malformed")
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(content)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    pt, ct, tt = _parse_usage(data)
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )
