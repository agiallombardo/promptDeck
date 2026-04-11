"""Resolve presentation access for signed-in users."""

from __future__ import annotations

import enum

from app.db.models.presentation import Presentation
from app.db.models.presentation_member import PresentationMember, PresentationMemberRole
from app.db.models.user import User, UserRole
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class PresentationAccess(enum.StrEnum):
    admin = "admin"
    owner = "owner"
    editor = "editor"
    user = "user"


async def resolve_access(
    db: AsyncSession,
    presentation: Presentation,
    user: User,
) -> PresentationAccess | None:
    if user.role == UserRole.admin:
        return PresentationAccess.admin
    if presentation.owner_id == user.id:
        return PresentationAccess.owner
    stmt = select(PresentationMember).where(
        PresentationMember.presentation_id == presentation.id,
        PresentationMember.revoked_at.is_(None),
        or_(
            PresentationMember.user_id == user.id,
            (
                (PresentationMember.principal_tenant_id == user.entra_tenant_id)
                & (PresentationMember.principal_entra_object_id == user.entra_object_id)
            ),
        ),
    )
    result = await db.execute(stmt)
    members = list(result.scalars().all())
    if not members:
        return None
    # More than one row can match (e.g. same user_id on rows with different principals).
    # Grant the strongest deck role present.
    if any(m.role == PresentationMemberRole.editor for m in members):
        return PresentationAccess.editor
    return PresentationAccess.user


def can_read(access: PresentationAccess | None) -> bool:
    return access is not None


def can_write_comments(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner, PresentationAccess.editor)


def can_manage_presentation(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner, PresentationAccess.editor)


def can_delete_presentation(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner)
