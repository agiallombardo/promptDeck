"""Deck HTML edits via LiteLLM (OpenAI-compatible HTTP), OpenAI SDK, or Anthropic SDK."""

from __future__ import annotations

import re
from base64 import b64encode
from dataclasses import dataclass
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

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


def _to_data_url(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{b64encode(data).decode('ascii')}"


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


async def complete_diagram_json_edit(
    *,
    api_base: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    image_bytes: bytes | None = None,
    image_media_type: str | None = None,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    user_content: Any = user_message
    if image_bytes is not None and image_media_type:
        user_content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": _to_data_url(image_media_type, image_bytes)},
            },
        ]
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
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
    if not isinstance(msg, dict):
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


def _openai_message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return "".join(parts)
    return ""


async def complete_deck_html_edit_openai(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    async with AsyncOpenAI(**kwargs) as client:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
        )
    raw = resp.choices[0].message.content
    text = _openai_message_text(raw)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = resp.usage
    pt = _usage_int(u.prompt_tokens) if u is not None else None
    ct = _usage_int(u.completion_tokens) if u is not None else None
    tt = _usage_int(u.total_tokens) if u is not None else None
    if tt is None and pt is not None and ct is not None:
        tt = pt + ct
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )


async def complete_diagram_json_edit_openai(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    image_bytes: bytes | None = None,
    image_media_type: str | None = None,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    user_content: Any = user_message
    if image_bytes is not None and image_media_type:
        user_content = [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": _to_data_url(image_media_type, image_bytes)},
            },
        ]
    async with AsyncOpenAI(**kwargs) as client:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
    raw = resp.choices[0].message.content
    text = _openai_message_text(raw)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = resp.usage
    pt = _usage_int(u.prompt_tokens) if u is not None else None
    ct = _usage_int(u.completion_tokens) if u is not None else None
    tt = _usage_int(u.total_tokens) if u is not None else None
    if tt is None and pt is not None and ct is not None:
        tt = pt + ct
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )


async def complete_deck_html_edit_anthropic(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    async with AsyncAnthropic(**kwargs) as client:
        msg = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.2,
        )
    parts: list[str] = []
    for block in msg.content:
        if block.type == "text":
            parts.append(block.text)
    text = "".join(parts)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = msg.usage
    pt = _usage_int(u.input_tokens)
    ct = _usage_int(u.output_tokens)
    tt = (pt + ct) if pt is not None and ct is not None else None
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )


async def complete_diagram_json_edit_anthropic(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_message: str,
    image_bytes: bytes | None = None,
    image_media_type: str | None = None,
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    user_content: list[dict[str, Any]] = [{"type": "text", "text": user_message}]
    if image_bytes is not None and image_media_type:
        user_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": b64encode(image_bytes).decode("ascii"),
                },
            }
        )
    async with AsyncAnthropic(**kwargs) as client:
        msg = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],  # type: ignore[arg-type]
            temperature=0.2,
        )
    parts: list[str] = []
    for block in msg.content:
        if block.type == "text":
            parts.append(block.text)
    text = "".join(parts)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = msg.usage
    pt = _usage_int(u.input_tokens)
    ct = _usage_int(u.output_tokens)
    tt = (pt + ct) if pt is not None and ct is not None else None
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )


def _openai_user_content_multimodal(
    user_text: str, image_attachments: list[tuple[bytes, str]]
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for img_b, mt in image_attachments:
        parts.append(
            {"type": "image_url", "image_url": {"url": _to_data_url(mt, img_b)}},
        )
    return parts


async def complete_deck_html_edit_multimodal(
    *,
    api_base: str,
    api_key: str | None,
    model: str,
    system_prompt: str,
    user_text: str,
    image_attachments: list[tuple[bytes, str]],
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _openai_user_content_multimodal(user_text, image_attachments),
            },
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


async def complete_deck_html_edit_openai_multimodal(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_text: str,
    image_attachments: list[tuple[bytes, str]],
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    user_content: Any = _openai_user_content_multimodal(user_text, image_attachments)
    async with AsyncOpenAI(**kwargs) as client:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
        )
    raw = resp.choices[0].message.content
    text = _openai_message_text(raw)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = resp.usage
    pt = _usage_int(u.prompt_tokens) if u is not None else None
    ct = _usage_int(u.completion_tokens) if u is not None else None
    tt = _usage_int(u.total_tokens) if u is not None else None
    if tt is None and pt is not None and ct is not None:
        tt = pt + ct
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )


async def complete_deck_html_edit_anthropic_multimodal(
    *,
    api_key: str,
    base_url: str | None,
    model: str,
    system_prompt: str,
    user_text: str,
    image_attachments: list[tuple[bytes, str]],
    timeout_seconds: float = 300.0,
) -> DeckLlmCompletionResult:
    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
    bu = (base_url or "").strip().rstrip("/")
    if bu:
        kwargs["base_url"] = bu
    user_content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
    for img_b, mt in image_attachments:
        user_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mt,
                    "data": b64encode(img_b).decode("ascii"),
                },
            }
        )
    async with AsyncAnthropic(**kwargs) as client:
        msg = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],  # type: ignore[arg-type]
            temperature=0.2,
        )
    parts: list[str] = []
    for block in msg.content:
        if block.type == "text":
            parts.append(block.text)
    text = "".join(parts)
    if not text.strip():
        raise ValueError("LLM returned empty content")
    out = strip_markdown_fenced_html(text)
    if len(out) > _MAX_COMPLETION_CHARS:
        raise ValueError("LLM output too large")
    u = msg.usage
    pt = _usage_int(u.input_tokens)
    ct = _usage_int(u.output_tokens)
    tt = (pt + ct) if pt is not None and ct is not None else None
    return DeckLlmCompletionResult(
        text=out, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt
    )
