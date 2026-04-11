"""Zip-slip and path traversal guards for zip bundle uploads."""

from __future__ import annotations


def is_safe_bundle_path(name: str) -> bool:
    """
    Return False if `name` (archive member path) could escape the extraction root.
    Reject '..', POSIX-absolute paths, and empty / all-dot segments.
    """
    raw = name.replace("\\", "/").strip()
    if raw.startswith("/"):
        return False
    norm = raw.strip("/")
    if not norm:
        return False
    for segment in norm.split("/"):
        if segment in ("", ".", ".."):
            return False
        if segment.startswith("/"):
            return False
    return True
