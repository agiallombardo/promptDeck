from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.deck_prompt_job import DeckPromptJob, DeckPromptJobStatus
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.models.user import User
from app.db.session import get_db
from app.deps import PresentationGrant, get_current_user, get_presentation_editor
from app.jobs.deck_prompt_runner import run_deck_prompt_job
from app.rate_limit import limiter
from app.schemas.deck_prompt import DeckPromptJobCreate, DeckPromptJobRead
from app.services.acl import can_manage_presentation, resolve_access
from app.services.audit import client_ip_from_request, record_audit

router = APIRouter(tags=["deck-prompt-jobs"])


@router.post(
    "/presentations/{presentation_id}/deck-prompt-jobs",
    response_model=DeckPromptJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def create_deck_prompt_job(
    request: Request,
    body: DeckPromptJobCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> DeckPromptJobRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    presentation = grant.presentation
    if presentation.current_version_id is None:
        raise HTTPException(status_code=400, detail="No active version; upload HTML first")

    ver = await db.get(PresentationVersion, presentation.current_version_id)
    if ver is None or ver.presentation_id != presentation.id:
        raise HTTPException(status_code=400, detail="Current version not found")
    if ver.storage_kind != "single_html":
        raise HTTPException(
            status_code=400,
            detail="Only single-file HTML decks support prompt editing",
        )

    job = DeckPromptJob(
        presentation_id=presentation.id,
        source_version_id=ver.id,
        prompt=body.prompt.strip(),
        is_generation=False,
        status=DeckPromptJobStatus.queued,
        progress=0,
        status_message="Queued",
        created_by=grant.user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await record_audit(
        db,
        actor_id=grant.user.id,
        action="presentation.deck_prompt.created",
        target_kind="deck_prompt_job",
        target_id=job.id,
        metadata={"presentation_id": str(presentation.id), "source_version_id": str(ver.id)},
        client_ip=client_ip_from_request(request),
    )

    background_tasks.add_task(run_deck_prompt_job, job.id)
    return DeckPromptJobRead.model_validate(job)


@router.get("/deck-prompt-jobs/{job_id}", response_model=DeckPromptJobRead)
async def get_deck_prompt_job(
    job_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeckPromptJobRead:
    job = await db.get(DeckPromptJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    pres = await db.get(Presentation, job.presentation_id)
    if pres is None or pres.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Presentation not found")
    access = await resolve_access(db, pres, user)
    if not can_manage_presentation(access):
        raise HTTPException(status_code=403, detail="Forbidden")
    return DeckPromptJobRead.model_validate(job)
