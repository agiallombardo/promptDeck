"""OpenAI-compatible chat completion for deck HTML editing."""

from __future__ import annotations

import re
from typing import Any

import httpx

_MAX_COMPLETION_CHARS = 512_000


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
) -> str:
    """Call POST {api_base}/chat/completions; return assistant text (stripped fences)."""
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
    choices = data.get("choices")
    if not choices:
        raise ValueError("LLM response missing choices")
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(content)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    return out
