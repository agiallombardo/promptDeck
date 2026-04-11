"""Inline relative CSS/JS into a single HTML file for simple zip bundles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.storage.local import safe_join, version_dir

if TYPE_CHECKING:
    from app.config import Settings

UNSUPPORTED_BUNDLE_MESSAGE = (
    "This type of web framework or multi-chunk build is not supported yet. "
    "Export a single-file or simple static HTML/CSS/JS deck, or upload one .html file."
)

_MAX_JS_FILES = 10
_FORBIDDEN_SUBSTRINGS = (
    "node_modules/",
    "vite.config",
    "webpack.config",
    "rollup.config",
    "parcel",
    ".next/",
    "dist/assets/",  # common hashed chunk layout hint
)

_LINK_RE = re.compile(r"<link\s+[^>]+>", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script\s+[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
_SRC_RE = re.compile(r'src\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def _forbidden_paths(root: Path) -> None:
    try:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix().lower()
            for bad in _FORBIDDEN_SUBSTRINGS:
                if bad in rel:
                    raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
    except ValueError:
        raise
    except OSError as e:
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE) from e


def _count_js_files(root: Path) -> int:
    n = 0
    try:
        for p in root.rglob("*.js"):
            if p.is_file():
                n += 1
                if n > _MAX_JS_FILES:
                    return n
    except OSError:
        return 999
    return n


def _same_bundle_url(url: str) -> bool:
    u = url.strip()
    if not u or u.startswith("#") or u.startswith("data:") or u.startswith("javascript:"):
        return False
    if u.startswith("//") or "://" in u:
        return False
    return True


def _read_text_under(parent: Path, rel: str) -> str:
    rel_norm = rel.replace("\\", "/").lstrip("/")
    target = (parent / rel_norm).resolve()
    parent_r = parent.resolve()
    try:
        target.relative_to(parent_r)
    except ValueError as e:
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE) from e
    if not target.is_file():
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE) from e


def inline_zip_entry_to_single_html(
    settings: Settings,
    storage_prefix: str,
    entry_path: str,
) -> tuple[str, bytes]:
    """
    Read entry HTML from extracted bundle, inline local CSS/JS, return (new_entry_path, html_bytes).
    """
    root = version_dir(settings, storage_prefix)
    _forbidden_paths(root)
    if _count_js_files(root) > _MAX_JS_FILES:
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)

    try:
        entry_file = safe_join(root, entry_path.replace("\\", "/"))
    except ValueError as e:
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE) from e
    if not entry_file.is_file():
        raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
    entry_parent = entry_file.parent
    html = entry_file.read_text(encoding="utf-8", errors="replace")

    # Stylesheets
    def repl_link(m: re.Match[str]) -> str:
        tag = m.group(0)
        if "stylesheet" not in tag.lower():
            return tag
        hm = _HREF_RE.search(tag)
        if not hm:
            return tag
        href = hm.group(1)
        if not _same_bundle_url(href):
            raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
        rel_path = href.split("#")[0].split("?")[0]
        css = _read_text_under(entry_parent, rel_path)
        return f"<style>\n/* inlined: {rel_path} */\n{css}\n</style>"

    html = _LINK_RE.sub(repl_link, html)

    # Scripts
    def repl_script(m: re.Match[str]) -> str:
        tag = m.group(0)
        if "src=" not in tag.lower():
            return tag
        if re.search(r'type\s*=\s*["\']module["\']', tag, re.I):
            raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
        sm = _SRC_RE.search(tag)
        if not sm:
            return tag
        src = sm.group(1)
        if not _same_bundle_url(src):
            raise ValueError(UNSUPPORTED_BUNDLE_MESSAGE)
        rel_path = src.split("#")[0].split("?")[0]
        js = _read_text_under(entry_parent, rel_path)
        return f"<script>\n/* inlined: {rel_path} */\n{js}\n</script>"

    html = _SCRIPT_RE.sub(repl_script, html)

    out_name = "__promptdeck_inlined.html"
    out_bytes = html.encode("utf-8")
    return out_name, out_bytes
