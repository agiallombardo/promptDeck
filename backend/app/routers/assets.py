from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.session import get_db
from app.security.asset_signing import verify_asset
from app.storage.local import read_bytes_if_exists

router = APIRouter(prefix="/a", tags=["assets"])

ASSET_CSP = (
    "default-src 'self'; "
    "script-src 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'unsafe-inline' 'self'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'self'"
)

_PROBE_PATH = Path(__file__).resolve().parent.parent / "probe" / "probe.js"


def _probe_js() -> str:
    return _PROBE_PATH.read_text(encoding="utf-8")


def _inject_probe(html: bytes) -> bytes:
    text = html.decode("utf-8", errors="replace")
    lower = text.lower()
    idx = lower.find("</head>")
    probe = f'<script data-promptdeck-probe="1">\n{_probe_js()}\n</script>'
    if idx != -1:
        out = text[:idx] + probe + text[idx:]
    else:
        out = probe + text
    return out.encode("utf-8")


def _norm_rel(p: str) -> str:
    return p.replace("\\", "/").strip("/")


@router.get("/{version_id}/{file_path:path}")
async def serve_asset(
    version_id: uuid.UUID,
    file_path: str,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    exp: Annotated[int, Query(..., description="Unix expiry time")],
    sig: Annotated[str, Query(..., min_length=1)],
    sub: Annotated[uuid.UUID, Query(..., description="User id")],
    role: Annotated[str, Query(..., min_length=1)],
) -> Response:
    if not verify_asset(
        settings,
        version_id=version_id,
        exp=exp,
        sig=sig,
        user_id=sub,
        role=role,
    ):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    result = await db.execute(
        select(PresentationVersion).where(PresentationVersion.id == version_id),
    )
    ver = result.scalar_one_or_none()
    if ver is None:
        raise HTTPException(status_code=404, detail="Version not found")

    pres_result = await db.execute(
        select(Presentation).where(
            Presentation.id == ver.presentation_id,
            Presentation.deleted_at.is_(None),
        )
    )
    pres = pres_result.scalar_one_or_none()
    if pres is None:
        raise HTTPException(status_code=404, detail="Presentation not found")

    rel = _norm_rel(file_path)
    entry = _norm_rel(ver.entry_path)
    if not rel:
        raise HTTPException(status_code=404, detail="Not found")

    data = read_bytes_if_exists(settings, ver.storage_prefix, rel)
    if data is None:
        raise HTTPException(status_code=404, detail="Not found")

    media_type, _enc = mimetypes.guess_type(rel)
    if media_type is None:
        media_type = "application/octet-stream"

    headers: dict[str, str] = {"Content-Security-Policy": ASSET_CSP}

    is_html = media_type in ("text/html", "application/xhtml+xml") or rel.lower().endswith(".html")
    if rel.lower() == entry.lower() and is_html:
        body = _inject_probe(data)
        return Response(
            content=body,
            media_type="text/html; charset=utf-8",
            headers=headers,
        )

    return Response(content=data, media_type=media_type, headers=headers)
