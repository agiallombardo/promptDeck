"""Audit log table for security events.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_kind", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_ts"), "audit_log", ["ts"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_ts"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_table("audit_log")
