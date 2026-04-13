"""High-fidelity native parsers for common diagram source formats."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _float(raw: str | None, fallback: float) -> float:
    if raw is None:
        return fallback
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not m:
        return fallback
    try:
        return float(m.group(0))
    except ValueError:
        return fallback


def parse_drawio_xml(text: str) -> dict | None:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    cells = [el for el in root.iter() if _local(el.tag) == "mxCell"]
    if not cells:
        return None

    nodes: list[dict] = []
    edges: list[dict] = []
    known: set[str] = set()
    for idx, c in enumerate(cells):
        cid = (c.attrib.get("id") or "").strip()
        if not cid:
            continue
        if c.attrib.get("vertex") == "1":
            geo = next((g for g in c if _local(g.tag) == "mxGeometry"), None)
            x = _float(geo.attrib.get("x") if geo is not None else None, (idx % 6) * 260.0)
            y = _float(geo.attrib.get("y") if geo is not None else None, (idx // 6) * 160.0)
            label = (c.attrib.get("value") or cid).strip()
            nodes.append(
                {
                    "id": cid,
                    "type": "default",
                    "position": {"x": x, "y": y},
                    "data": {"label": re.sub(r"<[^>]+>", "", label)},
                }
            )
            known.add(cid)
    for idx, c in enumerate(cells):
        if c.attrib.get("edge") != "1":
            continue
        src = (c.attrib.get("source") or "").strip()
        tgt = (c.attrib.get("target") or "").strip()
        if src in known and tgt in known:
            edges.append(
                {
                    "id": f"e{idx + 1}",
                    "source": src,
                    "target": tgt,
                    "type": "smoothstep",
                }
            )
    if not nodes:
        return None
    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


_MERMAID_EDGE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s*(?:\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\})?\s*[-=.]+>\s*"
    r"([A-Za-z0-9_]+)\s*(?:\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\})?\s*$"
)
_MERMAID_NODE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*([\[\(\{])(.*)([\]\)\}])\s*$")


def parse_mermaid_flowchart(text: str) -> dict | None:
    if "flowchart" not in text and "graph " not in text:
        return None
    labels: dict[str, str] = {}
    edges: list[dict] = []
    ids: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        m = _MERMAID_EDGE.match(line)
        if m:
            a, b = m.group(1), m.group(2)
            ids.add(a)
            ids.add(b)
            edges.append(
                {"id": f"e{len(edges) + 1}", "source": a, "target": b, "type": "smoothstep"}
            )
            continue
        n = _MERMAID_NODE.match(line)
        if n:
            nid = n.group(1)
            label = n.group(3).strip().strip('"')
            ids.add(nid)
            if label:
                labels[nid] = label
    if not ids:
        return None
    nodes = []
    for idx, nid in enumerate(sorted(ids)):
        nodes.append(
            {
                "id": nid,
                "type": "default",
                "position": {"x": (idx % 6) * 260.0, "y": (idx // 6) * 160.0},
                "data": {"label": labels.get(nid, nid)},
            }
        )
    return {
        "nodes": nodes,
        "edges": edges,
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


def parse_vsdx(raw: bytes) -> dict | None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile:
        return None
    try:
        page_names = [
            n for n in zf.namelist() if n.startswith("visio/pages/page") and n.endswith(".xml")
        ]
        if not page_names:
            return None
        nodes: list[dict] = []
        edges: list[dict] = []
        known: set[str] = set()
        for page in page_names[:8]:
            try:
                root = ET.fromstring(zf.read(page))
            except ET.ParseError:
                continue
            shapes = [el for el in root.iter() if _local(el.tag) == "Shape"]
            for idx, s in enumerate(shapes):
                sid = (s.attrib.get("ID") or "").strip()
                if not sid:
                    continue
                txt = ""
                for t in s.iter():
                    if _local(t.tag) == "Text" and t.text:
                        txt = t.text.strip()
                        break
                pinx = piny = None
                for c in s.iter():
                    if _local(c.tag) == "Cell":
                        n = (c.attrib.get("N") or "").strip()
                        if n == "PinX":
                            pinx = _float(c.attrib.get("V"), None)  # type: ignore[arg-type]
                        elif n == "PinY":
                            piny = _float(c.attrib.get("V"), None)  # type: ignore[arg-type]
                x = (pinx if pinx is not None else (idx % 6) * 2.6) * 100.0
                y = (piny if piny is not None else (idx // 6) * 1.6) * 100.0
                nid = f"shape_{sid}"
                if nid in known:
                    continue
                known.add(nid)
                nodes.append(
                    {
                        "id": nid,
                        "type": "default",
                        "position": {"x": x, "y": y},
                        "data": {"label": txt or nid},
                    }
                )
            for conn in [el for el in root.iter() if _local(el.tag) == "Connect"]:
                src = (conn.attrib.get("FromSheet") or "").strip()
                tgt = (conn.attrib.get("ToSheet") or "").strip()
                a = f"shape_{src}"
                b = f"shape_{tgt}"
                if a in known and b in known:
                    edges.append(
                        {
                            "id": f"e{len(edges) + 1}",
                            "source": a,
                            "target": b,
                            "type": "smoothstep",
                        }
                    )
        if not nodes:
            return None
        return {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1},
        }
    finally:
        zf.close()


def parse_native_diagram_source(filename: str, raw: bytes) -> dict | None:
    low = filename.lower()
    ext = Path(low).suffix
    if ext in {".drawio", ".xml"}:
        out = parse_drawio_xml(raw.decode("utf-8", errors="replace"))
        if out is not None:
            return out
    if ext in {".mmd", ".mermaid", ".txt", ".md"}:
        out = parse_mermaid_flowchart(raw.decode("utf-8", errors="replace"))
        if out is not None:
            return out
    if ext == ".vsdx":
        out = parse_vsdx(raw)
        if out is not None:
            return out
    if ext == ".zip":
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw), "r")
        except zipfile.BadZipFile:
            return None
        try:
            for name in zf.namelist():
                if name.endswith("/") or "__MACOSX/" in name or name.endswith(".DS_Store"):
                    continue
                inner = zf.read(name)
                parsed = parse_native_diagram_source(name, inner)
                if parsed is not None:
                    return parsed
        finally:
            zf.close()
    return None
