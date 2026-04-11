from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.export_job import ExportJob, ExportStatus
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User
from app.db.session import get_db
from app.deps import PresentationGrant, get_current_user, get_presentation_editor
from app.jobs.export_runner import run_export_job
from app.schemas.export import ExportCreate, ExportJobRead
from app.services.acl import can_manage_presentation, resolve_access
from app.services.audit import client_ip_from_request, record_audit

router = APIRouter(tags=["exports"])


@router.post(
    "/presentations/{presentation_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export_job(
    request: Request,
    body: ExportCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> ExportJobRead:
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
        options=dict(body.options),
        status=ExportStatus.queued,
        created_by=grant.user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await record_audit(
        db,
        actor_id=grant.user.id,
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
