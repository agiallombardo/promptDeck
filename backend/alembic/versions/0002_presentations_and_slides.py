"""Presentations, versions, slides.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_presentations_owner_id"), "presentations", ["owner_id"], unique=False)

    op.create_table(
        "presentation_versions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("storage_kind", sa.String(length=32), nullable=False),
        sa.Column("storage_prefix", sa.String(length=1024), nullable=False),
        sa.Column("entry_path", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("presentation_id", "version_number", name="uq_pres_version_num"),
    )
    op.create_index(
        op.f("ix_presentation_versions_presentation_id"),
        "presentation_versions",
        ["presentation_id"],
        unique=False,
    )

    op.create_table(
        "slides",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("selector", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["version_id"], ["presentation_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "index", name="uq_slide_version_idx"),
    )
    op.create_index(op.f("ix_slides_version_id"), "slides", ["version_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_slides_version_id"), table_name="slides")
    op.drop_table("slides")
    op.drop_index(
        op.f("ix_presentation_versions_presentation_id"),
        table_name="presentation_versions",
    )
    op.drop_table("presentation_versions")
    op.drop_index(op.f("ix_presentations_owner_id"), table_name="presentations")
    op.drop_table("presentations")
