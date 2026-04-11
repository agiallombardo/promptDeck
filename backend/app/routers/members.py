from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models.presentation_member import PresentationMember
from app.db.models.user import User
from app.db.session import get_db
from app.deps import PresentationGrant, get_presentation_editor
from app.schemas.member import (
    PresentationMemberCreate,
    PresentationMemberListResponse,
    PresentationMemberRead,
    PresentationMemberUpdate,
)
from app.services.audit import client_ip_from_request, record_audit
from app.services.entra_runtime import resolve_entra_oidc_config

router = APIRouter(tags=["members"])


async def _matching_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    object_id: str,
) -> User | None:
    result = await db.execute(
        select(User).where(
            User.entra_tenant_id == tenant_id,
            User.entra_object_id == object_id,
            User.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


@router.get(
    "/presentations/{presentation_id}/members",
    response_model=PresentationMemberListResponse,
)
async def list_presentation_members(
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationMemberListResponse:
    result = await db.execute(
        select(PresentationMember)
        .where(
            PresentationMember.presentation_id == grant.presentation.id,
            PresentationMember.revoked_at.is_(None),
        )
        .order_by(PresentationMember.created_at.asc())
    )
    return PresentationMemberListResponse(
        items=[PresentationMemberRead.model_validate(row) for row in result.scalars().all()]
    )


@router.post(
    "/presentations/{presentation_id}/members",
    response_model=PresentationMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_presentation_member(
    request: Request,
    body: PresentationMemberCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationMemberRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    cfg = await resolve_entra_oidc_config(db, settings)
    tenant_id = (cfg.tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Microsoft Entra tenant is not configured")
    if (
        grant.user.entra_object_id == body.entra_object_id
        and grant.user.entra_tenant_id == tenant_id
    ):
        raise HTTPException(status_code=400, detail="Owner/editor already has direct access")

    existing = await db.execute(
        select(PresentationMember).where(
            PresentationMember.presentation_id == grant.presentation.id,
            PresentationMember.principal_tenant_id == tenant_id,
            PresentationMember.principal_entra_object_id == body.entra_object_id,
        )
    )
    row = existing.scalar_one_or_none()
    linked_user = await _matching_user(db, tenant_id=tenant_id, object_id=body.entra_object_id)
    if row is None:
        row = PresentationMember(
            presentation_id=grant.presentation.id,
            role=body.role,
            principal_tenant_id=tenant_id,
            principal_entra_object_id=body.entra_object_id,
            principal_email=body.email.lower(),
            principal_display_name=body.display_name,
            principal_user_type=body.user_type,
            user_id=linked_user.id if linked_user is not None else None,
            granted_by=grant.user.id,
        )
        db.add(row)
    else:
        row.role = body.role
        row.principal_email = body.email.lower()
        row.principal_display_name = body.display_name
        row.principal_user_type = body.user_type
        row.user_id = linked_user.id if linked_user is not None else row.user_id
        row.revoked_at = None
    await db.commit()
    await db.refresh(row)
    await record_audit(
        db,
        actor_id=grant.user.id,
        action="presentation.member.upserted",
        target_kind="presentation_member",
        target_id=row.id,
        metadata={
            "presentation_id": str(grant.presentation.id),
            "principal_email": row.principal_email,
            "role": row.role.value,
        },
        client_ip=client_ip_from_request(request),
    )
    return PresentationMemberRead.model_validate(row)


@router.patch(
    "/presentations/{presentation_id}/members/{member_id}",
    response_model=PresentationMemberRead,
)
async def update_presentation_member(
    request: Request,
    member_id: uuid.UUID,
    body: PresentationMemberUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> PresentationMemberRead:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    row = await db.get(PresentationMember, member_id)
    if row is None or row.presentation_id != grant.presentation.id or row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Member not found")
    row.role = body.role
    await db.commit()
    await db.refresh(row)
    await record_audit(
        db,
        actor_id=grant.user.id,
        action="presentation.member.updated",
        target_kind="presentation_member",
        target_id=row.id,
        metadata={"presentation_id": str(grant.presentation.id), "role": row.role.value},
        client_ip=client_ip_from_request(request),
    )
    return PresentationMemberRead.model_validate(row)


@router.delete(
    "/presentations/{presentation_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_presentation_member(
    request: Request,
    member_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    grant: Annotated[PresentationGrant, Depends(get_presentation_editor)],
) -> None:
    if grant.user is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    row = await db.get(PresentationMember, member_id)
    if row is None or row.presentation_id != grant.presentation.id or row.revoked_at is not None:
        raise HTTPException(status_code=404, detail="Member not found")
    row.revoked_at = datetime.now(UTC)
    await db.commit()
    await record_audit(
        db,
        actor_id=grant.user.id,
        action="presentation.member.revoked",
        target_kind="presentation_member",
        target_id=row.id,
        metadata={"presentation_id": str(grant.presentation.id)},
        client_ip=client_ip_from_request(request),
    )
