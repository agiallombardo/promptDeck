"""Deck prompt edit jobs (LLM).

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deck_prompt_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["result_version_id"],
            ["presentation_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["presentation_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deck_prompt_jobs_presentation_id"),
        "deck_prompt_jobs",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deck_prompt_jobs_source_version_id"),
        "deck_prompt_jobs",
        ["source_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_deck_prompt_jobs_source_version_id"), table_name="deck_prompt_jobs")
    op.drop_index(op.f("ix_deck_prompt_jobs_presentation_id"), table_name="deck_prompt_jobs")
    op.drop_table("deck_prompt_jobs")
