"""Extract presentation zip bundles (multi-file HTML apps) to version storage."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

from app.services.zip_safety import is_safe_bundle_path
from app.storage.local import write_bytes_under

if TYPE_CHECKING:
    from app.config import Settings

# Archive and extracted limits (defense in depth vs zip bombs / huge trees).
MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_ZIP_UNCOMPRESSED_TOTAL = 80 * 1024 * 1024
MAX_ZIP_FILES = 800
MAX_ZIP_MEMBER_BYTES = 25 * 1024 * 1024


def _norm_zip_name(name: str) -> str:
    return name.replace("\\", "/").strip()


def choose_bundle_entrypoint(html_paths: list[str]) -> str:
    """
    Pick the HTML entry for the iframe: shallowest index.html, else a single .html file.
    """
    index_names = frozenset({"index.html", "index.htm"})
    index_candidates = [p for p in html_paths if p.lower().rsplit("/", 1)[-1] in index_names]
    if index_candidates:
        return min(index_candidates, key=lambda p: (p.count("/"), len(p), p))
    if len(html_paths) == 1:
        return html_paths[0]
    raise ValueError("Zip must include an index.html (or index.htm), or exactly one .html file")


def extract_zip_bundle(settings: Settings, storage_prefix: str, raw: bytes) -> str:
    """
    Write all safe regular files from `raw` under `storage_prefix`.
    Returns stored entry_path (posix slashes) for embed URLs.
    """
    if len(raw) > MAX_ZIP_BYTES:
        raise ValueError(f"Zip file too large (max {MAX_ZIP_BYTES // (1024 * 1024)}MB)")

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile as e:
        raise ValueError("Invalid or corrupted zip file") from e

    try:
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"Zip failed integrity check (member: {bad})")

        members: list[tuple[zipfile.ZipInfo, str]] = []
        uncompressed_total = 0

        for zi in zf.infolist():
            if zi.is_dir():
                continue
            name = _norm_zip_name(zi.filename)
            if not name or name.startswith("__MACOSX/") or name.endswith(".DS_Store"):
                continue
            if not is_safe_bundle_path(name):
                raise ValueError("Zip contains an unsafe path (possible path traversal)")
            uncompressed_total += zi.file_size
            if uncompressed_total > MAX_ZIP_UNCOMPRESSED_TOTAL:
                raise ValueError("Zip uncompressed size too large")
            if zi.file_size > MAX_ZIP_MEMBER_BYTES:
                raise ValueError("Zip contains a file that is too large")
            members.append((zi, name))

        if len(members) > MAX_ZIP_FILES:
            raise ValueError("Zip contains too many files")

        if not members:
            raise ValueError("Zip contains no files to extract")

        html_paths = [
            n for _, n in members if n.lower().endswith(".html") or n.lower().endswith(".htm")
        ]
        entry_path = choose_bundle_entrypoint(html_paths)

        for zi, name in members:
            data = zf.read(zi)
            if len(data) > MAX_ZIP_MEMBER_BYTES:
                raise ValueError("Zip member expanded larger than allowed")
            write_bytes_under(settings, storage_prefix, name, data)

        return entry_path
    finally:
        zf.close()
