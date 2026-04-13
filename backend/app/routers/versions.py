from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db.models.presentation import PresentationKind, PresentationVersion, Slide
from app.db.session import get_db
from app.deps import PresentationGrant, get_presentation_editor, get_presentation_reader
from app.logging_channels import LogChannel, channel_logger
from app.rate_limit import limiter
from app.schemas.presentation import (
    PresentationCodeRead,
    PresentationCodeUpdate,
    SlideRead,
    VersionRead,
)
from app.services.app_logging import write_app_log
from app.services.audit import client_ip_from_request, record_audit
from app.services.bundle_upload import extract_zip_bundle
from app.services.diagram_import import convert_uploaded_source_to_diagram
from app.services.diagram_schema import normalize_diagram_document
from app.services.diagram_version import persist_new_diagram_version
from app.services.html_bundle import inline_zip_entry_to_single_html
from app.services.llm_runtime import LlmNotConfiguredError, resolve_deck_llm_credentials
from app.services.presentation_code import extract_managed_code, merge_managed_code
from app.services.single_html_version import persist_new_single_html_version
from app.services.slide_manifest import build_slide_manifest
from app.storage.local import (
    presentation_prefix,
    read_bytes_if_exists,
    version_dir,
    write_bytes_under,
)

router = APIRouter(
    prefix="/presentations/{presentation_id}/versions",
    tags=["versions"],
)
log = channel_logger(LogChannel.audit)
MAX_SINGLE_HTML_BYTES = 10 * 1024 * 1024


def _remove_version_storage(settings: Settings, storage_prefix: str) -> None:
    """Best-effort delete of a version directory (failed zip / abandoned upload)."""
    root = version_dir(settings, storage_prefix)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)


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


def _code_read(version_id: uuid.UUID, html: str) -> PresentationCodeRead:
    css, js = extract_managed_code(html)
    return PresentationCodeRead(version_id=version_id, html=html, css=css, js=js)


async def _log_code_event(
    *,
    db: AsyncSession,
    request: Request,
    actor_id: uuid.UUID | None,
    presentation_id: uuid.UUID,
    source_version_id: uuid.UUID | None,
    result_version_id: uuid.UUID | None,
    event: str,
    action: str,
    status_code: int,
    level: str,
    error: str | None = None,
) -> None:
    payload: dict[str, str | None] = {
        "presentation_id": str(presentation_id),
        "source_version_id": str(source_version_id) if source_version_id else None,
        "result_version_id": str(result_version_id) if result_version_id else None,
    }
    if error is not None:
        payload["error"] = error
    await write_app_log(
        db,
        channel=LogChannel.audit,
        level=level,
        event=event,
        request_id=getattr(request.state, "request_id", None),
        user_id=actor_id,
        path=str(request.url.path),
        method=request.method,
        status_code=status_code,
        latency_ms=None,
        payload=payload,
        auto_commit=False,
    )
    await record_audit(
        db,
        actor_id=actor_id,
        action=action,
        target_kind="presentation_version" if result_version_id else "presentation",
        target_id=result_version_id or presentation_id,
        metadata=payload,
        client_ip=client_ip_from_request(request),
    )
    await db.commit()


@router.post("", response_model=VersionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_html_version(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> VersionRead:
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    name = file.filename or "index.html"
    lower = name.lower()
    presentation = grant.presentation
    pres_id = presentation.id
    actor_id = grant.user.id if grant.user is not None else None

    if presentation.kind == PresentationKind.diagram:
        try:
            if lower.endswith(".json"):
                parsed = json.loads(raw.decode("utf-8", errors="replace"))
                doc = normalize_diagram_document(parsed)
            else:
                if actor_id is None:
                    raise HTTPException(status_code=403, detail="Forbidden")
                try:
                    resolved = await resolve_deck_llm_credentials(db, settings, actor_id)
                except LlmNotConfiguredError as e:
                    raise HTTPException(status_code=503, detail=str(e)) from e
                converted = await convert_uploaded_source_to_diagram(
                    settings=settings,
                    resolved=resolved,
                    filename=name,
                    raw=raw,
                )
                doc = normalize_diagram_document(
                    json.loads(converted.document_text),
                )
            ver2 = await persist_new_diagram_version(
                settings=settings,
                db=db,
                presentation_id=pres_id,
                diagram_document=doc,
                origin="upload_import",
                created_by=actor_id,
            )
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            detail = str(e)
            if "conflict" in detail.lower():
                raise HTTPException(status_code=409, detail="Upload conflict; retry upload") from e
            raise HTTPException(status_code=500, detail=detail) from e
        slide_count = len(ver2.slides)
        log.info(
            "presentation.version.uploaded",
            presentation_id=str(pres_id),
            version_id=str(ver2.id),
            version_number=ver2.version_number,
            slide_count=slide_count,
        )
        await write_app_log(
            db,
            channel=LogChannel.audit,
            level="info",
            event="presentation.version.uploaded",
            request_id=getattr(request.state, "request_id", None),
            user_id=actor_id,
            path=str(request.url.path),
            method=request.method,
            status_code=201,
            latency_ms=None,
            payload={
                "presentation_id": str(pres_id),
                "version_id": str(ver2.id),
                "version_number": ver2.version_number,
                "slide_count": slide_count,
                "imported_filename": name,
            },
        )
        await record_audit(
            db,
            actor_id=actor_id,
            action="presentation.version.uploaded",
            target_kind="presentation_version",
            target_id=ver2.id,
            metadata={
                "presentation_id": str(pres_id),
                "version_number": ver2.version_number,
                "slide_count": slide_count,
                "imported_filename": name,
            },
            client_ip=client_ip_from_request(request),
        )
        await db.commit()
        return _version_read(ver2)

    if lower.endswith(".html") or lower.endswith(".htm"):
        try:
            ver2 = await persist_new_single_html_version(
                settings=settings,
                db=db,
                presentation_id=pres_id,
                html_bytes=raw,
                entry_filename=name,
                origin="upload",
                created_by=actor_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            detail = str(e)
            if "conflict" in detail.lower():
                raise HTTPException(status_code=409, detail="Upload conflict; retry upload") from e
            raise HTTPException(status_code=500, detail=detail) from e
        slide_count = len(ver2.slides)
        log.info(
            "presentation.version.uploaded",
            presentation_id=str(pres_id),
            version_id=str(ver2.id),
            version_number=ver2.version_number,
            slide_count=slide_count,
        )
        await write_app_log(
            db,
            channel=LogChannel.audit,
            level="info",
            event="presentation.version.uploaded",
            request_id=getattr(request.state, "request_id", None),
            user_id=actor_id,
            path=str(request.url.path),
            method=request.method,
            status_code=201,
            latency_ms=None,
            payload={
                "presentation_id": str(pres_id),
                "version_id": str(ver2.id),
                "version_number": ver2.version_number,
                "slide_count": slide_count,
            },
        )
        await record_audit(
            db,
            actor_id=actor_id,
            action="presentation.version.uploaded",
            target_kind="presentation_version",
            target_id=ver2.id,
            metadata={
                "presentation_id": str(pres_id),
                "version_number": ver2.version_number,
                "slide_count": slide_count,
            },
            client_ip=client_ip_from_request(request),
        )
        await db.commit()
        return _version_read(ver2)

    result = await db.execute(
        select(func.coalesce(func.max(PresentationVersion.version_number), 0)).where(
            PresentationVersion.presentation_id == presentation.id,
        )
    )
    next_num = int(result.scalar_one() or 0) + 1
    storage_prefix = presentation_prefix(presentation.id, next_num)

    sha256 = hashlib.sha256(raw).hexdigest()
    manifest: list[dict[str, Any]]
    entry_path: str
    storage_kind: str

    try:
        if lower.endswith(".zip"):
            entry_path = extract_zip_bundle(settings, storage_prefix, raw)
            try:
                new_entry, inlined = inline_zip_entry_to_single_html(
                    settings, storage_prefix, entry_path
                )
            except ValueError as e:
                _remove_version_storage(settings, storage_prefix)
                raise HTTPException(status_code=400, detail=str(e)) from e
            root = version_dir(settings, storage_prefix)
            shutil.rmtree(root, ignore_errors=True)
            root.mkdir(parents=True)
            write_bytes_under(settings, storage_prefix, new_entry, inlined)
            entry_path = new_entry
            storage_kind = "single_html"
            manifest = build_slide_manifest(inlined)
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Expected a .html, .htm, or .zip bundle "
                    "(zip should contain index.html and assets, e.g. a site export)"
                ),
            )
    except ValueError as e:
        if lower.endswith(".zip"):
            _remove_version_storage(settings, storage_prefix)
        raise HTTPException(status_code=400, detail=str(e)) from e

    ver = PresentationVersion(
        presentation_id=presentation.id,
        version_number=next_num,
        origin="upload",
        created_by=actor_id,
        storage_kind=storage_kind,
        storage_prefix=storage_prefix,
        entry_path=entry_path,
        sha256=sha256,
        size_bytes=len(raw),
    )
    db.add(ver)
    await db.flush()

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
        user_id=actor_id,
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
    await record_audit(
        db,
        actor_id=actor_id,
        action="presentation.version.uploaded",
        target_kind="presentation_version",
        target_id=ver2.id,
        metadata={
            "presentation_id": str(presentation.id),
            "version_number": ver2.version_number,
            "slide_count": len(manifest),
        },
        client_ip=client_ip_from_request(request),
    )

    return _version_read(ver2)


@router.get("", response_model=list[VersionRead])
async def list_versions(
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
) -> list[VersionRead]:
    result = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.presentation_id == grant.presentation.id)
        .order_by(PresentationVersion.version_number.desc())
        .options(selectinload(PresentationVersion.slides))
    )
    rows = result.scalars().all()
    return [_version_read(v) for v in rows]


@router.get("/current/code", response_model=PresentationCodeRead)
async def get_current_version_code(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationCodeRead:
    presentation = grant.presentation
    actor_id = grant.user.id if grant.user is not None else None

    if presentation.current_version_id is None:
        msg = "No active version; upload HTML first"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=None,
            result_version_id=None,
            event="presentation.code.load.failed",
            action="presentation.code.load.failed",
            status_code=400,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=400, detail=msg)

    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None or ver.presentation_id != presentation.id:
        msg = "Current version not found"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=presentation.current_version_id,
            result_version_id=None,
            event="presentation.code.load.failed",
            action="presentation.code.load.failed",
            status_code=404,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=404, detail=msg)
    if ver.storage_kind != "single_html":
        msg = "Only single-file HTML decks support code editing"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=ver.id,
            result_version_id=None,
            event="presentation.code.load.failed",
            action="presentation.code.load.failed",
            status_code=400,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=400, detail=msg)

    data = read_bytes_if_exists(settings, ver.storage_prefix, ver.entry_path)
    if data is None:
        msg = "Deck file missing from storage"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=ver.id,
            result_version_id=None,
            event="presentation.code.load.failed",
            action="presentation.code.load.failed",
            status_code=404,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=404, detail=msg)

    html = data.decode("utf-8", errors="replace")
    await _log_code_event(
        db=db,
        request=request,
        actor_id=actor_id,
        presentation_id=presentation.id,
        source_version_id=ver.id,
        result_version_id=None,
        event="presentation.code.load.succeeded",
        action="presentation.code.load.succeeded",
        status_code=200,
        level="info",
    )
    return _code_read(ver.id, html)


@router.put("/current/code", response_model=VersionRead, status_code=status.HTTP_201_CREATED)
async def save_current_version_code(
    request: Request,
    body: PresentationCodeUpdate,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> VersionRead:
    presentation = grant.presentation
    actor_id = grant.user.id if grant.user is not None else None

    if presentation.current_version_id is None:
        msg = "No active version; upload HTML first"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=None,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=400,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=400, detail=msg)

    source_version_id = presentation.current_version_id
    if source_version_id != body.base_version_id:
        msg = "Deck changed since editor opened; reload code and try again"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=source_version_id,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=409,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=409, detail=msg)

    ver = await db.get(PresentationVersion, source_version_id)
    if ver is None or ver.presentation_id != presentation.id:
        msg = "Current version not found"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=source_version_id,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=404,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=404, detail=msg)
    if ver.storage_kind != "single_html":
        msg = "Only single-file HTML decks support code editing"
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=source_version_id,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=400,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=400, detail=msg)

    merged_html = merge_managed_code(html=body.html, css=body.css, js=body.js)

    try:
        ver_new = await persist_new_single_html_version(
            settings=settings,
            db=db,
            presentation_id=presentation.id,
            html_bytes=merged_html.encode("utf-8"),
            entry_filename=ver.entry_path or "index.html",
            origin="code_edit",
            created_by=actor_id,
        )
    except ValueError as e:
        msg = str(e)
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=source_version_id,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=400,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=400, detail=msg) from e
    except RuntimeError as e:
        msg = str(e)
        code = 409 if "conflict" in msg.lower() else 500
        await _log_code_event(
            db=db,
            request=request,
            actor_id=actor_id,
            presentation_id=presentation.id,
            source_version_id=source_version_id,
            result_version_id=None,
            event="presentation.code.save.failed",
            action="presentation.code.save.failed",
            status_code=code,
            level="warning",
            error=msg,
        )
        raise HTTPException(status_code=code, detail=msg) from e

    await _log_code_event(
        db=db,
        request=request,
        actor_id=actor_id,
        presentation_id=presentation.id,
        source_version_id=source_version_id,
        result_version_id=ver_new.id,
        event="presentation.code.save.succeeded",
        action="presentation.code.save.succeeded",
        status_code=201,
        level="info",
    )
    return _version_read(ver_new)


@router.post("/{version_id}/activate", response_model=VersionRead)
async def activate_version(
    version_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> VersionRead:
    result = await db.execute(
        select(PresentationVersion)
        .where(
            PresentationVersion.id == version_id,
            PresentationVersion.presentation_id == grant.presentation.id,
        )
        .options(selectinload(PresentationVersion.slides))
    )
    ver = result.scalar_one_or_none()
    if ver is None:
        raise HTTPException(status_code=404, detail="Version not found")
    grant.presentation.current_version_id = ver.id
    await db.commit()
    result3 = await db.execute(
        select(PresentationVersion)
        .where(PresentationVersion.id == version_id)
        .options(selectinload(PresentationVersion.slides))
    )
    out = result3.scalar_one()
    return _version_read(out)
