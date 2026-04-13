"""Convert uploaded source files (pdf/image/zip/diagram formats) into XYFlow JSON."""

from __future__ import annotations

import io
import json
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.services.deck_llm_completion import (
    DeckLlmCompletionResult,
    complete_diagram_json_edit,
    complete_diagram_json_edit_anthropic,
    complete_diagram_json_edit_openai,
)
from app.services.diagram_icons import format_icon_catalog
from app.services.diagram_parsers import parse_native_diagram_source
from app.services.diagram_schema import normalize_diagram_document
from app.services.llm_runtime import ResolvedDeckLlm
from pypdf import PdfReader

MAX_IMPORT_BYTES = 50 * 1024 * 1024
MAX_TEXT_CHARS = 180_000
_TEXT_EXTS = {
    ".drawio",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".mmd",
    ".puml",
    ".uml",
    ".dot",
    ".graphml",
    ".csv",
    ".txt",
    ".md",
    ".dio",
}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}

_DIAGRAM_FROM_SOURCE_SYSTEM = (
    "You are an expert diagram builder and converter.\n"
    "Your task is to convert user/source material into one valid XYFlow JSON document only.\n"
    "Return strict JSON object with keys: nodes, edges, viewport.\n"
    "Use directional flow and clean topology layout. For network/server/cloud diagrams, use icon "
    "field on each node data when appropriate from this allowlist: "
    f"{format_icon_catalog()}.\n"
    "Node shape: {id,type,position,data:{label,icon?}}. "
    "Edge shape: {id,source,target,type,label?}. No markdown."
)


@dataclass(frozen=True, slots=True)
class DiagramImportResult:
    document_text: str
    usage: DeckLlmCompletionResult


def _safe_decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _extract_text_from_zip(raw: bytes) -> str:
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile:
        return ""
    chunks: list[str] = []
    try:
        for name in zf.namelist():
            if name.endswith("/") or "__MACOSX/" in name or name.endswith(".DS_Store"):
                continue
            low = name.lower()
            ext = Path(low).suffix
            if ext in _TEXT_EXTS or low.endswith(".vsdx") or low.endswith(".vdx") or "page" in low:
                try:
                    chunks.append(f"\n# FILE: {name}\n{_safe_decode(zf.read(name))[:6000]}")
                except Exception:
                    continue
            if len("".join(chunks)) > MAX_TEXT_CHARS:
                break
    finally:
        zf.close()
    return "".join(chunks)[:MAX_TEXT_CHARS]


def _extract_source_text(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(raw))
        out: list[str] = []
        for p in reader.pages[:40]:
            out.append(p.extract_text() or "")
            if len("".join(out)) > MAX_TEXT_CHARS:
                break
        return "\n".join(out)[:MAX_TEXT_CHARS]
    if ext == ".zip":
        return _extract_text_from_zip(raw)
    if ext in _TEXT_EXTS:
        return _safe_decode(raw)[:MAX_TEXT_CHARS]
    return ""


def _image_media_type(filename: str, raw: bytes) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in _IMAGE_EXTS:
        return None
    mt = mimetypes.guess_type(filename)[0]
    if mt in {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp", "image/svg+xml"}:
        return mt
    # sniff fallback for common formats
    if raw.startswith(b"\x89PNG"):
        return "image/png"
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    return "image/png"


def _user_message(user_prompt: str | None, filename: str, extracted_text: str) -> str:
    brief = (user_prompt or "").strip()
    if not brief:
        brief = (
            "Convert this source into a clear diagram preserving important entities, "
            "relationships, "
            "and flow. Prefer left-to-right layout and concise labels."
        )
    source = extracted_text.strip() or (
        "(No extractable text; infer from file name/type and image if provided.)"
    )
    return (
        f"User conversion brief:\n{brief}\n\n"
        f"Uploaded source filename: {filename}\n\n"
        "Source content/extracted text follows:\n"
        f"---SOURCE_START---\n{source}\n---SOURCE_END---"
    )


async def convert_uploaded_source_to_diagram(
    *,
    settings: Settings,
    resolved: ResolvedDeckLlm,
    filename: str,
    raw: bytes,
    user_prompt: str | None = None,
) -> DiagramImportResult:
    del settings
    if not raw:
        raise ValueError("Empty file")
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("Uploaded file too large")

    parsed_native = parse_native_diagram_source(filename, raw)
    if parsed_native is not None:
        normalized = normalize_diagram_document(parsed_native)
        text = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
        usage = DeckLlmCompletionResult(
            text=text,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )
        return DiagramImportResult(document_text=text, usage=usage)

    source_text = _extract_source_text(filename, raw)
    media_type = _image_media_type(filename, raw)
    image_bytes = raw if media_type is not None else None
    user_msg = _user_message(user_prompt, filename, source_text)

    if resolved.kind == "litellm":
        assert resolved.api_base is not None
        usage = await complete_diagram_json_edit(
            api_base=resolved.api_base,
            api_key=resolved.api_key,
            model=resolved.model,
            system_prompt=_DIAGRAM_FROM_SOURCE_SYSTEM,
            user_message=user_msg,
            image_bytes=image_bytes,
            image_media_type=media_type,
        )
    elif resolved.kind == "openai":
        assert resolved.openai_api_key is not None
        usage = await complete_diagram_json_edit_openai(
            api_key=resolved.openai_api_key,
            base_url=resolved.openai_base_url,
            model=resolved.model,
            system_prompt=_DIAGRAM_FROM_SOURCE_SYSTEM,
            user_message=user_msg,
            image_bytes=image_bytes,
            image_media_type=media_type,
        )
    else:
        assert resolved.anthropic_api_key is not None
        usage = await complete_diagram_json_edit_anthropic(
            api_key=resolved.anthropic_api_key,
            base_url=resolved.anthropic_base_url,
            model=resolved.model,
            system_prompt=_DIAGRAM_FROM_SOURCE_SYSTEM,
            user_message=user_msg,
            image_bytes=image_bytes,
            image_media_type=media_type,
        )

    text = usage.text.strip()
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("Model did not return valid diagram JSON") from e
    return DiagramImportResult(document_text=text, usage=usage)
