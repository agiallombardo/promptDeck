"""Allow anonymous share-sourced comments and threads.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("comments") as batch_op:
            batch_op.alter_column(
                "author_id",
                existing_type=sa.Uuid(as_uuid=True),
                nullable=True,
            )
        with op.batch_alter_table("comment_threads") as batch_op:
            batch_op.alter_column(
                "created_by",
                existing_type=sa.Uuid(as_uuid=True),
                nullable=True,
            )
    else:
        op.alter_column(
            "comments",
            "author_id",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=True,
        )
        op.alter_column(
            "comment_threads",
            "created_by",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("comment_threads") as batch_op:
            batch_op.alter_column(
                "created_by",
                existing_type=sa.Uuid(as_uuid=True),
                nullable=False,
            )
        with op.batch_alter_table("comments") as batch_op:
            batch_op.alter_column(
                "author_id",
                existing_type=sa.Uuid(as_uuid=True),
                nullable=False,
            )
    else:
        op.alter_column(
            "comment_threads",
            "created_by",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=False,
        )
        op.alter_column(
            "comments",
            "author_id",
            existing_type=sa.Uuid(as_uuid=True),
            nullable=False,
        )
