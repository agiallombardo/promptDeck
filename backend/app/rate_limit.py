"""HTTP rate limiting (slowapi). Disabled when ENVIRONMENT=test."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    enabled=os.getenv("ENVIRONMENT", "development") != "test",
)
