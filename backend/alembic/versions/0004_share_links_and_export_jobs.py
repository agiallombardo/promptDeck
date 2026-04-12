"""Share links and export jobs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_share_links_presentation_id"),
        "share_links",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_share_links_token_hash"), "share_links", ["token_hash"], unique=False)

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["presentation_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_export_jobs_presentation_id"),
        "export_jobs",
        ["presentation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_export_jobs_version_id"),
        "export_jobs",
        ["version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_export_jobs_version_id"), table_name="export_jobs")
    op.drop_index(op.f("ix_export_jobs_presentation_id"), table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index(op.f("ix_share_links_token_hash"), table_name="share_links")
    op.drop_index(op.f("ix_share_links_presentation_id"), table_name="share_links")
    op.drop_table("share_links")
