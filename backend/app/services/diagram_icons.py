"""Shared icon taxonomy for diagram generation, validation, and rendering."""

from __future__ import annotations

from collections.abc import Iterable

DIAGRAM_ICON_GLYPH: dict[str, str] = {
    # Core technical / topology
    "cloud": "☁",
    "server": "🖥",
    "database": "🗄",
    "router": "📡",
    "switch": "🔀",
    "firewall": "🛡",
    "load_balancer": "⚖",
    "client": "👤",
    "service": "⚙",
    "storage": "💾",
    "queue": "📬",
    "api": "🔌",
    "worker": "🧰",
    "device": "📱",
    "container": "📦",
    "kubernetes": "☸",
    "vm": "🧱",
    "cdn": "🌐",
    "dns": "🧭",
    "vpn": "🔐",
    "gateway": "🚪",
    "cache": "⚡",
    "message_bus": "🚌",
    "etl": "🔄",
    "data_lake": "🛶",
    "warehouse": "🏭",
    "monitoring": "📈",
    "ci_cd": "🔁",
    "auth": "🔑",
    "secret": "🗝",
    "notebook": "📓",
    # Business / process
    "process": "🧩",
    "decision": "🔷",
    "start": "🟢",
    "end": "🏁",
    "document": "📄",
    "form": "📝",
    "user": "👤",
    "team": "👥",
    "role": "🎭",
    "approval": "✅",
    "task": "☑",
    "event": "📣",
    "kpi": "📊",
    "goal": "🎯",
    "risk": "⚠",
    "control": "🎛",
    "invoice": "🧾",
    "payment": "💳",
    "order": "📦",
    "customer": "🤝",
    "supplier": "🏢",
    "product": "📦",
    "sales": "💼",
    "marketing": "📣",
    "hr": "🧑‍💼",
    "finance": "💰",
    "support": "🛟",
    "project": "📁",
    "milestone": "🏁",
    "calendar": "📅",
    "email": "✉",
    "chat": "💬",
    "meeting": "📆",
    "crm": "🗂",
    "erp": "🏬",
    "legal": "⚖",
    "compliance": "📜",
}

ALLOWED_DIAGRAM_ICONS: frozenset[str] = frozenset(DIAGRAM_ICON_GLYPH.keys())


def format_icon_catalog(icon_names: Iterable[str] | None = None) -> str:
    names = sorted(set(icon_names or ALLOWED_DIAGRAM_ICONS))
    return ",".join(names)
