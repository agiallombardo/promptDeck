from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.export_job import ExportJob, ExportStatus
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User, UserRole
from app.db.session import get_db
from app.deps import get_current_user, get_presentation_owner
from app.jobs.export_runner import run_export_job
from app.schemas.export import ExportCreate, ExportJobRead

router = APIRouter(tags=["exports"])


def _can_view_job(user: User, pres: Presentation, job: ExportJob) -> bool:
    if user.role == UserRole.admin:
        return True
    if pres.owner_id == user.id:
        return True
    if job.created_by == user.id:
        return True
    return False


@router.post(
    "/presentations/{presentation_id}/exports",
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export_job(
    body: ExportCreate,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_owner)],
) -> ExportJob:
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
        created_by=user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    background_tasks.add_task(run_export_job, job.id)
    return job


@router.get("/exports/{job_id}", response_model=ExportJobRead)
async def get_export_job(
    job_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExportJob:
    job = await db.get(ExportJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    pres = await db.get(Presentation, job.presentation_id)
    if pres is None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    if not _can_view_job(user, pres, job):
        raise HTTPException(status_code=403, detail="Forbidden")
    return job
