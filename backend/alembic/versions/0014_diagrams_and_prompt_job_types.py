"""Add diagram support fields and prompt job type metadata.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "presentations",
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="deck"),
    )

    op.add_column(
        "deck_prompt_jobs",
        sa.Column("job_type", sa.String(length=32), nullable=False, server_default="deck_edit"),
    )
    op.execute(
        sa.text(
            "UPDATE deck_prompt_jobs "
            "SET job_type = CASE WHEN is_generation THEN 'deck_generate' ELSE 'deck_edit' END"
        )
    )

    op.add_column(
        "comment_threads",
        sa.Column("target_kind", sa.String(length=32), nullable=False, server_default="slide"),
    )
    op.add_column("comment_threads", sa.Column("target_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("comment_threads", "target_id")
    op.drop_column("comment_threads", "target_kind")
    op.drop_column("deck_prompt_jobs", "job_type")
    op.drop_column("presentations", "kind")
