"""Resolve presentation access for signed-in users and share-link principals."""

from __future__ import annotations

import enum

from app.db.models.presentation import Presentation
from app.db.models.share_link import ShareLink, ShareRole
from app.db.models.user import User, UserRole


class PresentationAccess(enum.StrEnum):
    """Strongest access level the principal has for this presentation."""

    admin = "admin"
    owner = "owner"
    share_editor = "share_editor"
    share_commenter = "share_commenter"
    share_viewer = "share_viewer"


def effective_access(
    presentation: Presentation,
    *,
    user: User | None = None,
    share_link: ShareLink | None = None,
) -> PresentationAccess | None:
    if user is not None:
        if user.role == UserRole.admin:
            return PresentationAccess.admin
        if presentation.owner_id == user.id:
            return PresentationAccess.owner
        return None
    if share_link is not None:
        sl = share_link
        if sl.presentation_id != presentation.id:
            return None
        if sl.role == ShareRole.viewer:
            return PresentationAccess.share_viewer
        if sl.role == ShareRole.commenter:
            return PresentationAccess.share_commenter
        if sl.role == ShareRole.editor:
            return PresentationAccess.share_editor
    return None


def can_read_presentation(
    presentation: Presentation,
    *,
    user: User | None = None,
    share_link: ShareLink | None = None,
) -> bool:
    return effective_access(presentation, user=user, share_link=share_link) is not None


def can_write_comments(
    presentation: Presentation,
    *,
    user: User | None = None,
    share_link: ShareLink | None = None,
) -> bool:
    """Thread create / reply / resolve. Site-wide viewers never comment, even as deck owner."""
    if user is not None and user.role == UserRole.viewer:
        return False
    access = effective_access(presentation, user=user, share_link=share_link)
    if access is None:
        return False
    return access in (
        PresentationAccess.admin,
        PresentationAccess.owner,
        PresentationAccess.share_editor,
        PresentationAccess.share_commenter,
    )


def can_owner_manage_presentation(user: User | None, presentation: Presentation) -> bool:
    """Upload, shares, exports — signed-in owner or admin only (no share JWT)."""
    if user is None:
        return False
    access = effective_access(presentation, user=user, share_link=None)
    return access in (PresentationAccess.admin, PresentationAccess.owner)
