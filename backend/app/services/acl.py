"""Resolve presentation access for signed-in users."""

from __future__ import annotations

import enum

from app.db.models.presentation import Presentation
from app.db.models.presentation_member import PresentationMember
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
    member = result.scalar_one_or_none()
    if member is None:
        return None
    return PresentationAccess.editor if member.role.value == "editor" else PresentationAccess.user


def can_read(access: PresentationAccess | None) -> bool:
    return access is not None


def can_write_comments(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner, PresentationAccess.editor)


def can_manage_presentation(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner, PresentationAccess.editor)


def can_delete_presentation(access: PresentationAccess | None) -> bool:
    return access in (PresentationAccess.admin, PresentationAccess.owner)
