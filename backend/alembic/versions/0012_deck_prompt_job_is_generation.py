"""Deck prompt jobs: is_generation flag (generate vs edit).

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deck_prompt_jobs",
        sa.Column("is_generation", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("deck_prompt_jobs", "is_generation", server_default=None)


def downgrade() -> None:
    op.drop_column("deck_prompt_jobs", "is_generation")
