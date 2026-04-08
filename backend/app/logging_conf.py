import logging

import structlog
from structlog.typing import EventDict, WrappedLogger


def _add_channel(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """Copy structlog logger name `app.<channel>` into `channel` for stdout JSON."""
    name = getattr(_logger, "name", "") or ""
    if name.startswith("app.") and "channel" not in event_dict:
        event_dict["channel"] = name.split(".", 1)[1]
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_channel,
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )
