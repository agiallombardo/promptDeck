from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.comment_thread import Comment, CommentThread, ThreadStatus
from app.db.models.presentation import Presentation, PresentationVersion
from app.db.session import get_db
from app.deps import (
    Principal,
    get_presentation_comment_writer,
    get_presentation_reader,
    get_principal,
)
from app.schemas.comment import (
    CommentCreate,
    CommentRead,
    ThreadCreate,
    ThreadListResponse,
    ThreadPatch,
    ThreadRead,
)
from app.services.acl import PresentationAccess, can_write_comments, effective_access

router = APIRouter(tags=["comments"])

SHARED_COMMENTER_LABEL = "Shared commenter"


async def _get_thread_for_comment_write(
    thread_id: uuid.UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommentThread:
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.id == thread_id)
        .options(selectinload(CommentThread.comments).selectinload(Comment.author))
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    pres = await db.get(Presentation, thread.presentation_id)
    if pres is None or pres.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presentation not found")
    if not can_write_comments(pres, user=principal.user, share_link=principal.share_link):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return thread


def _comment_read(c: Comment) -> CommentRead:
    if c.author is not None:
        name = c.author.display_name
    elif c.author_id is None:
        name = SHARED_COMMENTER_LABEL
    else:
        name = None
    return CommentRead(
        id=c.id,
        author_id=c.author_id,
        author_display_name=name,
        body=c.body,
        body_format=c.body_format,
        created_at=c.created_at,
        edited_at=c.edited_at,
    )


def _thread_read(thread: CommentThread) -> ThreadRead:
    alive = [c for c in thread.comments if c.deleted_at is None]
    alive.sort(key=lambda x: x.created_at)
    return ThreadRead(
        id=thread.id,
        presentation_id=thread.presentation_id,
        version_id=thread.version_id,
        slide_index=thread.slide_index,
        anchor_x=thread.anchor_x,
        anchor_y=thread.anchor_y,
        status=thread.status,
        created_by=thread.created_by,
        created_at=thread.created_at,
        resolved_at=thread.resolved_at,
        comments=[_comment_read(c) for c in alive],
    )


@router.get("/presentations/{presentation_id}/threads", response_model=ThreadListResponse)
async def list_threads(
    presentation: Annotated[Presentation, Depends(get_presentation_reader)],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_id: Annotated[uuid.UUID | None, Query(description="Filter by version")] = None,
) -> ThreadListResponse:
    vid = version_id
    if vid is None:
        vid = presentation.current_version_id
    if vid is None:
        return ThreadListResponse(items=[])

    result = await db.execute(
        select(CommentThread)
        .where(
            CommentThread.presentation_id == presentation.id,
            CommentThread.version_id == vid,
        )
        .options(selectinload(CommentThread.comments).selectinload(Comment.author))
        .order_by(CommentThread.created_at.desc())
    )
    rows = result.scalars().all()
    return ThreadListResponse(items=[_thread_read(t) for t in rows])


@router.post(
    "/presentations/{presentation_id}/threads",
    response_model=ThreadRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread(
    body: ThreadCreate,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    presentation: Annotated[Presentation, Depends(get_presentation_comment_writer)],
) -> ThreadRead:
    ver = await db.get(PresentationVersion, body.version_id)
    if ver is None or ver.presentation_id != presentation.id:
        raise HTTPException(status_code=400, detail="Invalid version for this presentation")

    author_id = principal.user.id if principal.user is not None else None
    created_by = author_id

    thread = CommentThread(
        presentation_id=presentation.id,
        version_id=body.version_id,
        slide_index=body.slide_index,
        anchor_x=body.anchor_x,
        anchor_y=body.anchor_y,
        status=ThreadStatus.open,
        created_by=created_by,
    )
    db.add(thread)
    await db.flush()
    db.add(
        Comment(
            thread_id=thread.id,
            author_id=author_id,
            body=body.first_comment,
            body_format="markdown",
        )
    )
    await db.commit()
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.id == thread.id)
        .options(selectinload(CommentThread.comments).selectinload(Comment.author))
    )
    out = result.scalar_one()
    return _thread_read(out)


@router.post("/threads/{thread_id}/comments", response_model=CommentRead, status_code=201)
async def add_comment(
    body: CommentCreate,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread: Annotated[CommentThread, Depends(_get_thread_for_comment_write)],
) -> CommentRead:
    author_id = principal.user.id if principal.user is not None else None
    c = Comment(
        thread_id=thread.id,
        author_id=author_id,
        body=body.body,
        body_format="markdown",
    )
    db.add(c)
    await db.commit()
    result = await db.execute(
        select(Comment).where(Comment.id == c.id).options(selectinload(Comment.author)),
    )
    row = result.scalar_one()
    return _comment_read(row)


@router.patch("/threads/{thread_id}", response_model=ThreadRead)
async def patch_thread(
    body: ThreadPatch,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread: Annotated[CommentThread, Depends(_get_thread_for_comment_write)],
) -> ThreadRead:
    thread.status = body.status
    if body.status == ThreadStatus.resolved:
        thread.resolved_at = datetime.now(UTC)
    else:
        thread.resolved_at = None
    await db.commit()
    result = await db.execute(
        select(CommentThread)
        .where(CommentThread.id == thread.id)
        .options(selectinload(CommentThread.comments).selectinload(Comment.author))
    )
    out = result.scalar_one()
    return _thread_read(out)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.thread))
    )
    comment = result.scalar_one_or_none()
    if comment is None or comment.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Comment not found")
    pres = await db.get(Presentation, comment.thread.presentation_id)
    if pres is None or pres.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Presentation not found")

    access = effective_access(pres, user=principal.user, share_link=principal.share_link)
    if access is None:
        raise HTTPException(status_code=403, detail="Forbidden")

    is_owner_or_admin = access in (PresentationAccess.admin, PresentationAccess.owner)
    is_author = (
        principal.user is not None
        and comment.author_id is not None
        and comment.author_id == principal.user.id
    )
    if not is_owner_or_admin and not is_author:
        raise HTTPException(status_code=403, detail="Forbidden")

    comment.deleted_at = datetime.now(UTC)
    await db.commit()
