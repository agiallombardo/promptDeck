from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation import PresentationKind
from app.db.models.presentation_source_artifact import (
    PresentationSourceArtifact,
    PresentationSourceArtifactIntent,
)
from app.db.session import get_db
from app.deps import PresentationGrant, get_presentation_editor, get_presentation_reader
from app.rate_limit import limiter
from app.schemas.presentation import (
    PresentationSourceArtifactListResponse,
    PresentationSourceArtifactRead,
    PresentationSourceArtifactUpdate,
)
from app.services.audit import client_ip_from_request, record_audit
from app.services.presentation_source_artifacts import (
    persist_source_artifact,
    remove_artifact_storage,
)

router = APIRouter(prefix="/presentations", tags=["presentation-source-artifacts"])

_DECK_ONLY = "Source artifacts are only for deck presentations"


def _parse_intent(raw: str) -> PresentationSourceArtifactIntent:
    s = raw.strip().lower()
    if s == PresentationSourceArtifactIntent.embed.value:
        return PresentationSourceArtifactIntent.embed
    if s == PresentationSourceArtifactIntent.inspire.value:
        return PresentationSourceArtifactIntent.inspire
    raise ValueError("intent must be 'embed' or 'inspire'")


@router.get(
    "/{presentation_id}/source-artifacts",
    response_model=PresentationSourceArtifactListResponse,
)
async def list_source_artifacts(
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_reader)],
) -> PresentationSourceArtifactListResponse:
    if grant.presentation.kind != PresentationKind.deck:
        raise HTTPException(status_code=400, detail=_DECK_ONLY)
    stmt = (
        select(PresentationSourceArtifact)
        .where(PresentationSourceArtifact.presentation_id == grant.presentation.id)
        .order_by(PresentationSourceArtifact.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return PresentationSourceArtifactListResponse(
        items=[PresentationSourceArtifactRead.model_validate(r) for r in rows],
    )


@router.post(
    "/{presentation_id}/source-artifacts",
    response_model=PresentationSourceArtifactRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def upload_source_artifact(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    intent: Annotated[str, Form(...)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationSourceArtifactRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if grant.presentation.kind != PresentationKind.deck:
        raise HTTPException(status_code=400, detail=_DECK_ONLY)
    try:
        parsed_intent = _parse_intent(intent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    raw = await file.read()
    try:
        row = await persist_source_artifact(
            settings=settings,
            db=db,
            presentation_id=grant.presentation.id,
            original_filename=file.filename or "upload",
            content_type=file.content_type,
            raw=raw,
            intent=parsed_intent,
            created_by=grant.user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await db.commit()
    await db.refresh(row)

    await record_audit(
        db,
        actor_id=grant.user.id,
        action="presentation.source_artifact.created",
        target_kind="presentation_source_artifact",
        target_id=row.id,
        metadata={
            "presentation_id": str(grant.presentation.id),
            "intent": parsed_intent.value,
            "filename": row.original_filename,
        },
        client_ip=client_ip_from_request(request),
    )

    return PresentationSourceArtifactRead.model_validate(row)


@router.patch(
    "/{presentation_id}/source-artifacts/{artifact_id}",
    response_model=PresentationSourceArtifactRead,
)
async def patch_source_artifact(
    artifact_id: uuid.UUID,
    body: PresentationSourceArtifactUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationSourceArtifactRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if grant.presentation.kind != PresentationKind.deck:
        raise HTTPException(status_code=400, detail=_DECK_ONLY)
    row = await db.get(PresentationSourceArtifact, artifact_id)
    if row is None or row.presentation_id != grant.presentation.id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    row.intent = PresentationSourceArtifactIntent(body.intent)
    await db.commit()
    await db.refresh(row)
    return PresentationSourceArtifactRead.model_validate(row)


@router.delete(
    "/{presentation_id}/source-artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_source_artifact(
    artifact_id: uuid.UUID,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> None:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if grant.presentation.kind != PresentationKind.deck:
        raise HTTPException(status_code=400, detail=_DECK_ONLY)
    row = await db.get(PresentationSourceArtifact, artifact_id)
    if row is None or row.presentation_id != grant.presentation.id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    remove_artifact_storage(settings, row)
    await db.delete(row)
    await db.commit()
