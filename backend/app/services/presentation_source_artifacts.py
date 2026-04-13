from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass

from app.config import Settings
from app.db.models.presentation_source_artifact import (
    PresentationSourceArtifact,
    PresentationSourceArtifactIntent,
)
from app.storage.local import (
    read_bytes_if_exists,
    sanitize_filename,
    version_dir,
    write_bytes_under,
)
from sqlalchemy.ext.asyncio import AsyncSession

MAX_SOURCE_ARTIFACT_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 32_000

_IMAGE_CT_PREFIX = "image/"


def storage_prefix_for_artifact(presentation_id: uuid.UUID, artifact_id: uuid.UUID) -> str:
    return f"presentations/{presentation_id}/source-artifacts/{artifact_id}"


def _guess_image_media_type(content_type: str | None, filename: str) -> str | None:
    ct = (content_type or "").strip().lower()
    if ct.startswith(_IMAGE_CT_PREFIX):
        return "image/jpeg" if ct == "image/jpg" else ct
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return None


def extract_text_or_note(*, filename: str, content_type: str | None, data: bytes) -> str:
    media = _guess_image_media_type(content_type, filename)
    if media is not None:
        return (
            f"[Binary image file: {filename!r}, {len(data)} bytes — shown as image attachment "
            "to the model.]"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return (
            f"[Non-text/binary file: {filename!r}, {len(data)} bytes, "
            f"content-type={content_type or 'unknown'} — no text extraction.]"
        )
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        text = text[:MAX_EXTRACTED_TEXT_CHARS] + "\n…[truncated]"
    return text


@dataclass(frozen=True, slots=True)
class ResolvedArtifactForLlm:
    artifact_id: uuid.UUID
    filename: str
    intent: PresentationSourceArtifactIntent
    text_excerpt: str
    image_bytes: bytes | None
    image_media_type: str | None


def resolve_bytes_for_llm(
    *,
    artifact: PresentationSourceArtifact,
    data: bytes,
) -> ResolvedArtifactForLlm:
    media = _guess_image_media_type(artifact.content_type, artifact.original_filename)
    if media is not None:
        excerpt = extract_text_or_note(
            filename=artifact.original_filename,
            content_type=artifact.content_type,
            data=data,
        )
        return ResolvedArtifactForLlm(
            artifact_id=artifact.id,
            filename=artifact.original_filename,
            intent=artifact.intent,
            text_excerpt=excerpt,
            image_bytes=data,
            image_media_type=media,
        )
    text = extract_text_or_note(
        filename=artifact.original_filename,
        content_type=artifact.content_type,
        data=data,
    )
    return ResolvedArtifactForLlm(
        artifact_id=artifact.id,
        filename=artifact.original_filename,
        intent=artifact.intent,
        text_excerpt=text,
        image_bytes=None,
        image_media_type=None,
    )


async def persist_source_artifact(
    *,
    settings: Settings,
    db: AsyncSession,
    presentation_id: uuid.UUID,
    original_filename: str,
    content_type: str | None,
    raw: bytes,
    intent: PresentationSourceArtifactIntent,
    created_by: uuid.UUID,
) -> PresentationSourceArtifact:
    if len(raw) == 0:
        raise ValueError("Empty file")
    if len(raw) > MAX_SOURCE_ARTIFACT_BYTES:
        raise ValueError(f"File too large (max {MAX_SOURCE_ARTIFACT_BYTES // (1024 * 1024)} MiB)")
    aid = uuid.uuid4()
    prefix = storage_prefix_for_artifact(presentation_id, aid)
    key = sanitize_filename(original_filename)
    write_bytes_under(settings, prefix, key, raw)
    sha = hashlib.sha256(raw).hexdigest()
    row = PresentationSourceArtifact(
        id=aid,
        presentation_id=presentation_id,
        original_filename=original_filename[:500],
        storage_prefix=prefix,
        object_key=key,
        content_type=(content_type[:255] if content_type else None),
        size_bytes=len(raw),
        sha256=sha,
        intent=intent,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row


def read_artifact_bytes(settings: Settings, artifact: PresentationSourceArtifact) -> bytes | None:
    return read_bytes_if_exists(settings, artifact.storage_prefix, artifact.object_key)


def remove_artifact_storage(settings: Settings, artifact: PresentationSourceArtifact) -> None:
    root = version_dir(settings, artifact.storage_prefix)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
