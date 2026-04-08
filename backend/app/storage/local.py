from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

from app.config import Settings


def version_dir(settings: Settings, storage_prefix: str) -> Path:
    return (settings.storage_root / storage_prefix).resolve()


def safe_join(base: Path, relative: str) -> Path:
    rel = relative.replace("\\", "/").strip("/")
    if not rel:
        return base.resolve()
    for part in rel.split("/"):
        if part in ("", ".", ".."):
            raise ValueError("invalid path")
    target = (base / rel).resolve()
    base_r = base.resolve()
    target.relative_to(base_r)
    return target


def write_bytes_under(
    settings: Settings,
    storage_prefix: str,
    relative_path: str,
    data: bytes,
) -> Path:
    base = version_dir(settings, storage_prefix)
    base.mkdir(parents=True, exist_ok=True)
    path = safe_join(base, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def read_bytes_if_exists(
    settings: Settings,
    storage_prefix: str,
    relative_path: str,
) -> bytes | None:
    base = version_dir(settings, storage_prefix)
    try:
        path = safe_join(base, relative_path)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path.read_bytes()


def presentation_prefix(presentation_id: UUID, version_number: int) -> str:
    return f"presentations/{presentation_id}/v{version_number}"


_slug_safe = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    return _slug_safe.sub("_", base)[:200] or "upload.html"
