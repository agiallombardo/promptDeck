"""Presentation source artifacts and deck prompt job links.

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentation_source_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("presentation_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("storage_prefix", sa.String(length=1024), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_presentation_source_artifacts_presentation_id"),
        "presentation_source_artifacts",
        ["presentation_id"],
        unique=False,
    )

    op.create_table(
        "deck_prompt_job_artifacts",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["presentation_source_artifacts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["deck_prompt_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "artifact_id"),
    )


def downgrade() -> None:
    op.drop_table("deck_prompt_job_artifacts")
    op.drop_index(
        op.f("ix_presentation_source_artifacts_presentation_id"),
        table_name="presentation_source_artifacts",
    )
    op.drop_table("presentation_source_artifacts")
