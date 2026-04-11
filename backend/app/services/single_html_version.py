"""Create a new presentation version from single-file HTML bytes (storage + DB)."""

from __future__ import annotations

import hashlib
import shutil
import uuid
from typing import Any

from app.config import Settings
from app.db.models.presentation import Presentation, PresentationVersion, Slide
from app.services.slide_manifest import build_slide_manifest
from app.storage.local import presentation_prefix, sanitize_filename, version_dir, write_bytes_under
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

MAX_SINGLE_HTML_BYTES = 10 * 1024 * 1024
_MAX_ATTEMPTS = 5


def _remove_version_storage(settings: Settings, storage_prefix: str) -> None:
    root = version_dir(settings, storage_prefix)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)


async def persist_new_single_html_version(
    *,
    settings: Settings,
    db: AsyncSession,
    presentation_id: uuid.UUID,
    html_bytes: bytes,
    entry_filename: str,
    origin: str,
    created_by: uuid.UUID | None,
) -> PresentationVersion:
    """Write HTML to storage, insert PresentationVersion + Slides, set current_version_id."""
    if len(html_bytes) == 0:
        raise ValueError("Empty HTML")
    if len(html_bytes) > MAX_SINGLE_HTML_BYTES:
        raise ValueError("HTML file too large (max 10MB)")

    sha256 = hashlib.sha256(html_bytes).hexdigest()
    manifest: list[dict[str, Any]] = build_slide_manifest(html_bytes)
    entry_path = sanitize_filename(entry_filename)
    ver2: PresentationVersion | None = None

    for attempt in range(_MAX_ATTEMPTS):
        await db.execute(
            select(Presentation.id).where(Presentation.id == presentation_id).with_for_update()
        )
        result = await db.execute(
            select(func.coalesce(func.max(PresentationVersion.version_number), 0)).where(
                PresentationVersion.presentation_id == presentation_id,
            )
        )
        next_num = int(result.scalar_one() or 0) + 1
        storage_prefix = f"{presentation_prefix(presentation_id, next_num)}-{uuid.uuid4().hex[:8]}"

        write_bytes_under(settings, storage_prefix, entry_path, html_bytes)

        ver = PresentationVersion(
            presentation_id=presentation_id,
            version_number=next_num,
            origin=origin,
            created_by=created_by,
            storage_kind="single_html",
            storage_prefix=storage_prefix,
            entry_path=entry_path,
            sha256=sha256,
            size_bytes=len(html_bytes),
        )
        db.add(ver)

        try:
            await db.flush()
        except IntegrityError as err:
            await db.rollback()
            _remove_version_storage(settings, storage_prefix)
            if attempt == _MAX_ATTEMPTS - 1:
                raise RuntimeError("Version conflict; retry") from err
            continue

        for item in manifest:
            db.add(
                Slide(
                    version_id=ver.id,
                    slide_index=item["index"],
                    selector=item["selector"],
                    title=item.get("title"),
                )
            )

        await db.execute(
            update(Presentation)
            .where(Presentation.id == presentation_id)
            .values(current_version_id=ver.id)
        )

        try:
            await db.commit()
        except IntegrityError as err:
            await db.rollback()
            _remove_version_storage(settings, storage_prefix)
            if attempt == _MAX_ATTEMPTS - 1:
                raise RuntimeError("Version conflict; retry") from err
            continue

        result2 = await db.execute(
            select(PresentationVersion)
            .where(PresentationVersion.id == ver.id)
            .options(selectinload(PresentationVersion.slides))
        )
        ver2 = result2.scalar_one_or_none()
        if ver2 is not None:
            break

    if ver2 is None:
        raise RuntimeError("Failed to store presentation version")

    return ver2
