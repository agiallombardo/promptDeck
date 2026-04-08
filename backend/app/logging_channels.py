"""Named log channels for structlog + app_logs (http, auth, audit, script)."""

from __future__ import annotations

import enum


class LogChannel(enum.StrEnum):
    """Stored in `app_logs.logger` and echoed in structlog as `channel`."""

    http = "http"
    auth = "auth"
    audit = "audit"
    script = "script"


def channel_logger(channel: LogChannel):
    """Structlog logger `app.<channel>` with bound `channel` for stdout JSON."""
    import structlog

    return structlog.get_logger(f"app.{channel.value}").bind(channel=channel.value)
