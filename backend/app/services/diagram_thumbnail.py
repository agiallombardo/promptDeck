"""Generate diagram thumbnails (PNG/JPG) for recent previews."""

from __future__ import annotations

import io
from typing import Any

from app.services.diagram_icons import DIAGRAM_ICON_GLYPH
from app.services.diagram_schema import normalize_diagram_document
from PIL import Image, ImageDraw

THUMB_W = 640
THUMB_H = 360
_NODE_W = 120
_NODE_H = 52


def generate_diagram_thumbnail_bytes(document: Any) -> tuple[bytes, bytes]:
    d = normalize_diagram_document(document)
    nodes = d["nodes"]
    edges = d["edges"]
    if nodes:
        min_x = min(float(n["position"]["x"]) for n in nodes)
        min_y = min(float(n["position"]["y"]) for n in nodes)
        max_x = max(float(n["position"]["x"]) for n in nodes) + _NODE_W
        max_y = max(float(n["position"]["y"]) for n in nodes) + _NODE_H
    else:
        min_x, min_y, max_x, max_y = 0.0, 0.0, 1280.0, 720.0
    scale_x = (THUMB_W - 24) / max(1.0, (max_x - min_x))
    scale_y = (THUMB_H - 24) / max(1.0, (max_y - min_y))
    scale = min(scale_x, scale_y, 1.0)

    img = Image.new("RGB", (THUMB_W, THUMB_H), color=(246, 248, 252))
    draw = ImageDraw.Draw(img)
    index = {n["id"]: n for n in nodes}

    def map_xy(x: float, y: float) -> tuple[float, float]:
        return (12 + (x - min_x) * scale, 12 + (y - min_y) * scale)

    for e in edges:
        s = index.get(e["source"])
        t = index.get(e["target"])
        if s is None or t is None:
            continue
        s_center_x = float(s["position"]["x"]) + (_NODE_W / 2)
        s_center_y = float(s["position"]["y"]) + (_NODE_H / 2)
        t_center_x = float(t["position"]["x"]) + (_NODE_W / 2)
        t_center_y = float(t["position"]["y"]) + (_NODE_H / 2)
        x1, y1 = map_xy(s_center_x, s_center_y)
        x2, y2 = map_xy(t_center_x, t_center_y)
        draw.line((x1, y1, x2, y2), fill=(96, 104, 124), width=2)

    for n in nodes:
        x = float(n["position"]["x"])
        y = float(n["position"]["y"])
        left, top = map_xy(x, y)
        right, bottom = map_xy(x + _NODE_W, y + _NODE_H)
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=8,
            fill=(233, 240, 255),
            outline=(37, 48, 65),
            width=1,
        )
        data = n.get("data") or {}
        label = str(data.get("label") or n["id"])[:30]
        icon_name = str(data.get("icon") or "")
        icon = DIAGRAM_ICON_GLYPH.get(icon_name, "")
        text = f"{icon} {label}".strip()
        draw.text((left + 8, top + 18), text, fill=(12, 22, 38))

    png_buf = io.BytesIO()
    jpg_buf = io.BytesIO()
    img.save(png_buf, format="PNG", optimize=True)
    img.save(jpg_buf, format="JPEG", quality=88, optimize=True)
    return png_buf.getvalue(), jpg_buf.getvalue()
