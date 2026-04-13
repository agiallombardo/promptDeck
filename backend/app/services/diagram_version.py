"""Create and read presentation versions for XYFlow diagram documents."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from typing import Any

from app.config import Settings
from app.db.models.presentation import Presentation, PresentationVersion, Slide
from app.services.diagram_schema import blank_diagram_document, normalize_diagram_document
from app.services.diagram_thumbnail import generate_diagram_thumbnail_bytes
from app.storage.local import (
    presentation_prefix,
    read_bytes_if_exists,
    version_dir,
    write_bytes_under,
)
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

_ENTRY_PATH = "diagram.json"
_MAX_ATTEMPTS = 5


def _remove_version_storage(settings: Settings, storage_prefix: str) -> None:
    root = version_dir(settings, storage_prefix)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)


def _normalized_document(raw: Any) -> dict[str, Any]:
    return normalize_diagram_document(raw)


def read_diagram_document(settings: Settings, version: PresentationVersion) -> dict[str, Any]:
    data = read_bytes_if_exists(settings, version.storage_prefix, version.entry_path)
    if data is None:
        raise ValueError("Diagram file missing from storage")
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        raise ValueError("Stored diagram is invalid JSON") from e
    return normalize_diagram_document(payload)


async def persist_new_diagram_version(
    *,
    settings: Settings,
    db: AsyncSession,
    presentation_id: uuid.UUID,
    diagram_document: Any,
    origin: str,
    created_by: uuid.UUID | None,
) -> PresentationVersion:
    normalized = _normalized_document(diagram_document)
    payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    thumb_png, thumb_jpg = generate_diagram_thumbnail_bytes(normalized)
    sha256 = hashlib.sha256(payload).hexdigest()
    ver2: PresentationVersion | None = None

    for attempt in range(_MAX_ATTEMPTS):
        await db.execute(
            select(Presentation.id).where(Presentation.id == presentation_id).with_for_update()
        )
        result = await db.execute(
            select(func.coalesce(func.max(PresentationVersion.version_number), 0)).where(
                PresentationVersion.presentation_id == presentation_id
            )
        )
        next_num = int(result.scalar_one() or 0) + 1
        storage_prefix = f"{presentation_prefix(presentation_id, next_num)}-{uuid.uuid4().hex[:8]}"

        write_bytes_under(settings, storage_prefix, _ENTRY_PATH, payload)
        write_bytes_under(settings, storage_prefix, "thumbnail.png", thumb_png)
        write_bytes_under(settings, storage_prefix, "thumbnail.jpg", thumb_jpg)
        ver = PresentationVersion(
            presentation_id=presentation_id,
            version_number=next_num,
            origin=origin,
            created_by=created_by,
            storage_kind="xyflow_json",
            storage_prefix=storage_prefix,
            entry_path=_ENTRY_PATH,
            sha256=sha256,
            size_bytes=len(payload),
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

        db.add(
            Slide(
                version_id=ver.id,
                slide_index=0,
                selector="diagram:root",
                title="Diagram",
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
        raise RuntimeError("Failed to store diagram version")
    return ver2


def starter_diagram_document() -> dict[str, Any]:
    return blank_diagram_document()
