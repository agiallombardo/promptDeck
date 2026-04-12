"""Comment threads and comments.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comment_threads",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("slide_index", sa.Integer(), nullable=False),
        sa.Column("anchor_x", sa.Float(), nullable=False),
        sa.Column("anchor_y", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["presentation_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_comment_threads_presentation_id"),
        "comment_threads",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_comment_threads_version_id"),
        "comment_threads",
        ["version_id"],
        unique=False,
    )
    op.create_index(
        "ix_comment_threads_pres_slide",
        "comment_threads",
        ["presentation_id", "slide_index"],
        unique=False,
    )

    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("thread_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("author_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_format", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["thread_id"], ["comment_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comments_thread_id"), "comments", ["thread_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comments_thread_id"), table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_comment_threads_pres_slide", table_name="comment_threads")
    op.drop_index(op.f("ix_comment_threads_version_id"), table_name="comment_threads")
    op.drop_index(op.f("ix_comment_threads_presentation_id"), table_name="comment_threads")
    op.drop_table("comment_threads")
