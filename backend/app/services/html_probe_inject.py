"""Inject slide probe script into HTML (shared by asset serving and PDF export)."""

from __future__ import annotations

from pathlib import Path

_PROBE_PATH = Path(__file__).resolve().parent.parent / "probe" / "probe.js"


def probe_js_source() -> str:
    return _PROBE_PATH.read_text(encoding="utf-8")


def inject_probe_into_html(html: bytes) -> bytes:
    text = html.decode("utf-8", errors="replace")
    lower = text.lower()
    idx = lower.find("</head>")
    probe = f'<script data-promptdeck-probe="1">\n{probe_js_source()}\n</script>'
    if idx != -1:
        out = text[:idx] + probe + text[idx:]
    else:
        out = probe + text
    return out.encode("utf-8")
