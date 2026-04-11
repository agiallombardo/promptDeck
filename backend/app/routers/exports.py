from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.export_job import ExportFormat, ExportJob, ExportStatus
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User
from app.db.session import get_db
from app.deps import PresentationGrant, get_current_user, get_presentation_editor
from app.jobs.export_runner import run_export_job
from app.rate_limit import limiter
from app.schemas.export import ExportCreate, ExportJobRead
from app.services.acl import can_manage_presentation, resolve_access
from app.services.audit import client_ip_from_request, record_audit

router = APIRouter(tags=["exports"])

_DEFAULT_EXPORT_OPTIONS: dict[str, object] = {
    "print_background": True,
    "landscape": True,
    "slide_settle_ms": 400,
    "page_width_css": "1280px",
    "page_height_css": "720px",
}


def _safe_download_basename(title: str) -> str:
    cleaned = re.sub(r"[^\w\-. ]+", "", title, flags=re.UNICODE).strip()
    return (cleaned or "presentation")[:80]


def _merge_export_options(body: ExportCreate) -> dict[str, object]:
    return {**_DEFAULT_EXPORT_OPTIONS, **dict(body.options)}


@router.post(
    "/presentations/{presentation_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("30/minute")
async def create_export_job(
    request: Request,
    body: ExportCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> ExportJobRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    actor_id = grant.user.id
    presentation = grant.presentation
    vid = body.version_id or presentation.current_version_id
    if vid is None:
        raise HTTPException(status_code=400, detail="No version to export; upload a deck first")
    ver = await db.get(PresentationVersion, vid)
    if ver is None or ver.presentation_id != presentation.id:
        raise HTTPException(status_code=400, detail="Invalid version for this presentation")

    job = ExportJob(
        presentation_id=presentation.id,
        version_id=ver.id,
        format=body.format,
        scope=dict(body.scope),
        options=_merge_export_options(body),
        status=ExportStatus.queued,
        created_by=actor_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await record_audit(
        db,
        actor_id=actor_id,
        action="export_job.created",
        target_kind="export_job",
        target_id=job.id,
        metadata={"presentation_id": str(presentation.id), "format": str(job.format)},
        client_ip=client_ip_from_request(request),
    )
    background_tasks.add_task(run_export_job, job.id)
    return ExportJobRead.model_validate(job)


@router.get("/exports/{job_id}", response_model=ExportJobRead)
async def get_export_job(
    job_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportJobRead:
    job = await db.get(ExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    pres = await db.get(Presentation, job.presentation_id)
    if pres is None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    access = await resolve_access(db, pres, user)
    if not can_manage_presentation(access):
        raise HTTPException(status_code=403, detail="Forbidden")
    return ExportJobRead.model_validate(job)


@router.get("/exports/{job_id}/file")
async def download_export_file(
    job_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    job = await db.get(ExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status != ExportStatus.succeeded or not job.output_path:
        raise HTTPException(status_code=400, detail="Export is not ready for download")
    pres = await db.get(Presentation, job.presentation_id)
    if pres is None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    access = await resolve_access(db, pres, user)
    if not can_manage_presentation(access):
        raise HTTPException(status_code=403, detail="Forbidden")
    path = Path(job.output_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Export file missing")
    base = _safe_download_basename(pres.title)
    if job.format == ExportFormat.single_html:
        name = f"{base}.html"
        media = "text/html; charset=utf-8"
    else:
        name = f"{base}.pdf"
        media = "application/pdf"
    return FileResponse(path, media_type=media, filename=name)
