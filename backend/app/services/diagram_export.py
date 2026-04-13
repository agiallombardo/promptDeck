"""Render diagram JSON to standalone HTML for preview/export."""

from __future__ import annotations

import html
from typing import Any

from app.services.diagram_icons import DIAGRAM_ICON_GLYPH
from app.services.diagram_schema import normalize_diagram_document

_NODE_W = 190.0
_NODE_H = 72.0
_PAD = 120.0


def render_diagram_html(document: Any, *, title: str = "Diagram") -> bytes:
    d = normalize_diagram_document(document)
    nodes = d["nodes"]
    edges = d["edges"]
    node_index = {n["id"]: n for n in nodes}

    if nodes:
        min_x = min(float(n["position"]["x"]) for n in nodes) - _PAD
        min_y = min(float(n["position"]["y"]) for n in nodes) - _PAD
        max_x = max(float(n["position"]["x"]) for n in nodes) + _NODE_W + _PAD
        max_y = max(float(n["position"]["y"]) for n in nodes) + _NODE_H + _PAD
    else:
        min_x, min_y, max_x, max_y = 0.0, 0.0, 1280.0, 720.0

    width = max(640.0, max_x - min_x)
    height = max(360.0, max_y - min_y)

    edge_lines: list[str] = []
    for e in edges:
        s = node_index.get(e["source"])
        t = node_index.get(e["target"])
        if s is None or t is None:
            continue
        x1 = float(s["position"]["x"]) + (_NODE_W / 2.0) - min_x
        y1 = float(s["position"]["y"]) + (_NODE_H / 2.0) - min_y
        x2 = float(t["position"]["x"]) + (_NODE_W / 2.0) - min_x
        y2 = float(t["position"]["y"]) + (_NODE_H / 2.0) - min_y
        edge_lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="edge" />'
        )

    node_boxes: list[str] = []
    for n in nodes:
        x = float(n["position"]["x"]) - min_x
        y = float(n["position"]["y"]) - min_y
        data = n.get("data") or {}
        label = html.escape(str(data.get("label") or n["id"]))
        icon_name = str(data.get("icon") or "")
        icon = DIAGRAM_ICON_GLYPH.get(icon_name, "")
        icon_html = f'<div class="icon">{html.escape(icon)}</div>' if icon else ""
        node_boxes.append(
            '<div class="node" style='
            f'"left:{x:.2f}px;top:{y:.2f}px;width:{_NODE_W:.0f}px;height:{_NODE_H:.0f}px;">'
            f"{icon_html}<span>{label}</span></div>"
        )

    out = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "html,body{margin:0;padding:0;background:#f7f7f8;font-family:ui-sans-serif,system-ui,sans-serif;}"
        ".canvas{position:relative;overflow:hidden;margin:0 auto;background:#fff;"
        "border:1px solid #ddd;box-sizing:border-box;}"
        ".edges{position:absolute;inset:0;}"
        ".edge{stroke:#69717f;stroke-width:2;stroke-linecap:round;}"
        ".node{position:absolute;border:1px solid #253041;border-radius:10px;background:#f2f5ff;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "padding:8px;box-sizing:border-box;"
        "font-size:13px;line-height:1.3;color:#0b1624;font-weight:600;text-align:center;}"
        ".icon{font-size:18px;line-height:1;margin-bottom:4px;}"
        "</style></head><body>"
        f'<div class="canvas" style="width:{width:.2f}px;height:{height:.2f}px;">'
        f'<svg class="edges" width="{width:.2f}" height="{height:.2f}" '
        f'viewBox="0 0 {width:.2f} {height:.2f}" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#69717f"/></marker></defs>'
        f'<g marker-end="url(#arrow)">{"".join(edge_lines)}</g></svg>'
        f"{''.join(node_boxes)}</div></body></html>"
    )
    return out.encode("utf-8")
