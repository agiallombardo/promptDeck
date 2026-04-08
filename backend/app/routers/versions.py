from __future__ import annotations

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db.models.presentation import Presentation, PresentationVersion, Slide
from app.db.models.user import User
from app.db.session import get_db
from app.deps import get_current_user, get_presentation
from app.logging_channels import LogChannel, channel_logger
from app.schemas.presentation import SlideRead, VersionRead
from app.services.app_logging import write_app_log
from app.services.slide_manifest import build_slide_manifest
from app.storage.local import presentation_prefix, sanitize_filename, write_bytes_under

router = APIRouter(
    prefix="/presentations/{presentation_id}/versions",
    tags=["versions"],
)
log = channel_logger(LogChannel.audit)
MAX_HTML_BYTES = 10 * 1024 * 1024


def _version_read(ver: PresentationVersion) -> VersionRead:
    slides = sorted(ver.slides, key=lambda s: s.slide_index)
    return VersionRead(
        id=ver.id,
        presentation_id=ver.presentation_id,
        version_number=ver.version_number,
        origin=ver.origin,
        storage_kind=ver.storage_kind,
        entry_path=ver.entry_path,
        sha256=ver.sha256,
        size_bytes=ver.size_bytes,
        created_at=ver.created_at,
        slides=[SlideRead.model_validate(s) for s in slides],
    )


@router.post("", response_model=VersionRead, status_code=status.HTTP_201_CREATED)
async def upload_html_version(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation)],
) -> VersionRead:
    raw = await file.read()
    if len(raw) > MAX_HTML_BYTES:
        raise HTTPException(status_code=413, detail="HTML file too large (max 10MB)")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    name = file.filename or "index.html"
    if not name.lower().endswith(".html"):
        raise HTTPException(status_code=400, detail="Expected a .html file for this upload")

    entry_path = sanitize_filename(name)
    sha256 = hashlib.sha256(raw).hexdigest()
    manifest = build_slide_manifest(raw)

    result = await db.execute(
        select(func.coalesce(func.max(PresentationVersion.version_number), 0)).where(
            PresentationVersion.presentation_id == presentation.id,
        )
    )
    next_num = int(result.scalar_one() or 0) + 1
    storage_prefix = presentation_prefix(presentation.id, next_num)

    ver = PresentationVersion(
        presentation_id=presentation.id,
        version_number=next_num,
        origin="upload",
        created_by=user.id,
        storage_kind="single_html",
        storage_prefix=storage_prefix,
        entry_path=entry_path,
        sha256=sha256,
        size_bytes=len(raw),
    )
    db.add(ver)
    await db.flush()

    write_bytes_under(settings, storage_prefix, entry_path, raw)

    for item in manifest:
        db.add(
            Slide(
                version_id=ver.id,
                slide_index=item["index"],
                selector=item["selector"],
                title=item.get("title"),
            )
        )

    presentation.current_version_id = ver.id
    await db.commit()

    await db.refresh(ver)
    result2 = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.id == ver.id)
        .options(selectinload(PresentationVersion.slides))
    )
    ver2 = result2.scalar_one()

    log.info(
        "presentation.version.uploaded",
        presentation_id=str(presentation.id),
        version_id=str(ver2.id),
        version_number=ver2.version_number,
        slide_count=len(manifest),
    )
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level="info",
        event="presentation.version.uploaded",
        request_id=getattr(request.state, "request_id", None),
        user_id=user.id,
        path=str(request.url.path),
        method=request.method,
        status_code=201,
        latency_ms=None,
        payload={
            "presentation_id": str(presentation.id),
            "version_id": str(ver2.id),
            "version_number": ver2.version_number,
            "slide_count": len(manifest),
        },
    )

    return _version_read(ver2)


@router.get("", response_model=list[VersionRead])
async def list_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation)],
) -> list[VersionRead]:
    result = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.presentation_id == presentation.id)
        .order_by(PresentationVersion.version_number.desc())
        .options(selectinload(PresentationVersion.slides))
    )
    rows = result.scalars().unique().all()
    return [_version_read(v) for v in rows]


@router.post("/{version_id}/activate", response_model=VersionRead)
async def activate_version(
    version_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation)],
) -> VersionRead:
    result = await db.execute(
        select(PresentationVersion)
        .where(
            PresentationVersion.id == version_id,
            PresentationVersion.presentation_id == presentation.id,
        )
        .options(selectinload(PresentationVersion.slides))
    )
    ver = result.scalar_one_or_none()
    if ver is None:
        raise HTTPException(status_code=404, detail="Version not found")
    presentation.current_version_id = ver.id
    await db.commit()
    result3 = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.id == version_id)
        .options(selectinload(PresentationVersion.slides))
    )
    out = result3.scalar_one()
    return _version_read(out)
