"""Validate and normalize XYFlow-compatible diagram JSON documents."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from app.services.diagram_icons import ALLOWED_DIAGRAM_ICONS

MAX_NODES = 500
MAX_EDGES = 1_500
MAX_LABEL_CHARS = 240
MAX_NODE_DATA_BYTES = 4_096

_SAFE_TEXT = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_ALLOWED_NODE_TYPES = frozenset({"default", "input", "output"})
_ALLOWED_EDGE_TYPES = frozenset(
    {"default", "straight", "step", "smoothstep", "simplebezier", "bezier"}
)


def blank_diagram_document() -> dict[str, Any]:
    return {"nodes": [], "edges": [], "viewport": {"x": 0.0, "y": 0.0, "zoom": 1.0}}


def _as_finite_float(value: Any, fallback: float) -> float:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        out = float(value)
        if math.isfinite(out):
            return out
    return fallback


def _clean_text(value: Any, *, default: str = "") -> str:
    if not isinstance(value, str):
        return default
    out = _SAFE_TEXT.sub("", value).strip()
    if len(out) > MAX_LABEL_CHARS:
        out = out[:MAX_LABEL_CHARS]
    return out


def _normalize_viewport(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "x": _as_finite_float(raw.get("x"), 0.0),
        "y": _as_finite_float(raw.get("y"), 0.0),
        "zoom": _as_finite_float(raw.get("zoom"), 1.0),
    }


def _safe_node_data(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    out: dict[str, Any] = {}
    label = _clean_text(raw.get("label"), default="")
    if label:
        out["label"] = label
    icon = _clean_text(raw.get("icon"), default="")
    if icon in ALLOWED_DIAGRAM_ICONS:
        out["icon"] = icon
    encoded = json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_NODE_DATA_BYTES:
        return {}
    return out


def normalize_diagram_document(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Diagram must be a JSON object")
    if "nodes" not in raw or "edges" not in raw:
        raise ValueError("Diagram requires nodes and edges")

    nodes_raw = raw.get("nodes")
    edges_raw = raw.get("edges")
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        raise ValueError("Diagram nodes/edges must be arrays")
    if len(nodes_raw) > MAX_NODES:
        raise ValueError(f"Diagram has too many nodes (max {MAX_NODES})")
    if len(edges_raw) > MAX_EDGES:
        raise ValueError(f"Diagram has too many edges (max {MAX_EDGES})")

    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for idx, row in enumerate(nodes_raw):
        if not isinstance(row, dict):
            raise ValueError("Diagram node entries must be objects")
        raw_id = row.get("id")
        node_id = _clean_text(raw_id, default="")
        if not node_id:
            raise ValueError("Each diagram node needs a non-empty id")
        if node_id in node_ids:
            raise ValueError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

        node_type = _clean_text(row.get("type"), default="default") or "default"
        if node_type not in _ALLOWED_NODE_TYPES:
            raise ValueError(f"Unsupported node type: {node_type}")

        pos = row.get("position")
        if not isinstance(pos, dict):
            pos = {}
        # Deterministic fallback keeps nodes visible even when model omits positions.
        x_fallback = float((idx % 6) * 260)
        y_fallback = float((idx // 6) * 160)
        x = _as_finite_float(pos.get("x"), x_fallback)
        y = _as_finite_float(pos.get("y"), y_fallback)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "position": {"x": x, "y": y},
                "data": _safe_node_data(row.get("data")),
            }
        )

    edges: list[dict[str, Any]] = []
    edge_ids: set[str] = set()
    for idx, row in enumerate(edges_raw):
        if not isinstance(row, dict):
            raise ValueError("Diagram edge entries must be objects")
        raw_id = row.get("id")
        edge_id = _clean_text(raw_id, default=f"e{idx + 1}")
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge id: {edge_id}")
        source = _clean_text(row.get("source"), default="")
        target = _clean_text(row.get("target"), default="")
        if source not in node_ids or target not in node_ids:
            raise ValueError("Edge source/target must reference existing node ids")
        edge_type = _clean_text(row.get("type"), default="default") or "default"
        if edge_type not in _ALLOWED_EDGE_TYPES:
            raise ValueError(f"Unsupported edge type: {edge_type}")
        label = _clean_text(row.get("label"), default="")
        out = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
        }
        if label:
            out["label"] = label
        edges.append(out)
        edge_ids.add(edge_id)

    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": _normalize_viewport(raw.get("viewport")),
    }
