"""Parse uploaded HTML to discover slides (multiple selectors → counter fallback → body)."""

from __future__ import annotations

import re
from typing import Any

from selectolax.parser import HTMLParser

_COUNTER_RE = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")


def _title_for_node(node: Any) -> str | None:
    attrs = node.attributes or {}
    return attrs.get("data-title") or attrs.get("title") or attrs.get("aria-label")


def _slides_from_selector(tree: HTMLParser, selector: str) -> list[dict[str, Any]]:
    nodes = tree.css(selector)
    if len(nodes) < 2:
        return []
    return [
        {
            "index": i,
            "selector": selector,
            "title": _title_for_node(node),
        }
        for i, node in enumerate(nodes)
    ]


def _counter_slide_count(tree: HTMLParser) -> int:
    max_total = 0
    for node in tree.css("body *"):
        text = (node.text() or "").strip()
        if not text or len(text) > 32:
            continue
        match = _COUNTER_RE.search(text)
        if not match:
            continue
        cur = int(match.group(1))
        total = int(match.group(2))
        if total >= 1 and 1 <= cur <= total:
            max_total = max(max_total, total)
    return max_total


def build_slide_manifest(html: bytes) -> list[dict[str, Any]]:
    text = html.decode("utf-8", errors="replace")
    tree = HTMLParser(text)

    for selector in (
        "[data-slide]",
        "[data-slide-index]",
        '[aria-roledescription="slide"]',
        "body > section",
        "main > section",
        "main > article.slide",
        "body article.slide",
    ):
        slides = _slides_from_selector(tree, selector)
        if slides:
            return slides

    body = tree.body
    if body is None:
        return [{"index": 0, "selector": "body", "title": None}]

    counter_count = _counter_slide_count(tree)
    if counter_count > 1:
        slides: list[dict[str, Any]] = []
        for i in range(counter_count):
            slides.append({"index": i, "selector": "virtual-counter", "title": None})
        return slides

    return [{"index": 0, "selector": "body", "title": None}]
