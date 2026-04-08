"""Parse uploaded HTML to discover slides (data-slide → section → single body)."""

from __future__ import annotations

from typing import Any

from selectolax.parser import HTMLParser


def build_slide_manifest(html: bytes) -> list[dict[str, Any]]:
    text = html.decode("utf-8", errors="replace")
    tree = HTMLParser(text)

    data_slides = tree.css("[data-slide]")
    if data_slides:
        slides: list[dict[str, Any]] = []
        for i, node in enumerate(data_slides):
            title = None
            if node.attributes:
                title = node.attributes.get("data-title") or node.attributes.get("title")
            slides.append(
                {
                    "index": i,
                    "selector": "[data-slide]",
                    "title": title,
                }
            )
        return slides

    body = tree.body
    if body is None:
        return [{"index": 0, "selector": "body", "title": None}]

    sections = [c for c in body.iter() if c.tag == "section"]
    if sections:
        return [
            {
                "index": i,
                "selector": "body > section",
                "title": None,
            }
            for i in range(len(sections))
        ]

    return [{"index": 0, "selector": "body", "title": None}]
