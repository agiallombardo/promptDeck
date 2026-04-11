from __future__ import annotations

import uuid
from typing import Any

from app.db.models.audit_log import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession


def client_ip_from_request(request: Any) -> str | None:
    """Best-effort client IP: reverse-proxy headers first, then the transport peer."""
    headers = getattr(request, "headers", None)
    if headers is not None:
        xff = headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
        xri = headers.get("x-real-ip")
        if xri:
            return xri.strip()
    client = getattr(request, "client", None)
    if client is None:
        return None
    return client.host


async def record_audit(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_kind: str | None = None,
    target_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_kind=target_kind,
            target_id=target_id,
            metadata_=metadata,
            ip=client_ip,
        )
    )
    await session.commit()
