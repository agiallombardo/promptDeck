"""Deck prompt jobs: LLM model and token usage.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "deck_prompt_jobs",
        sa.Column("llm_model", sa.String(length=128), nullable=True),
    )
    op.add_column("deck_prompt_jobs", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "deck_prompt_jobs",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column("deck_prompt_jobs", sa.Column("total_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("deck_prompt_jobs", "total_tokens")
    op.drop_column("deck_prompt_jobs", "completion_tokens")
    op.drop_column("deck_prompt_jobs", "prompt_tokens")
    op.drop_column("deck_prompt_jobs", "llm_model")
