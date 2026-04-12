"""Per-provider LLM columns on users (OpenAI, Anthropic, LiteLLM).

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("llm_openai_base_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("llm_anthropic_base_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("llm_litellm_base_url", sa.String(length=512), nullable=True),
    )
    op.add_column("users", sa.Column("llm_openai_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("llm_anthropic_key_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("llm_litellm_key_encrypted", sa.Text(), nullable=True))
    op.execute(
        text(
            "UPDATE users SET llm_openai_key_encrypted = llm_api_key_encrypted "
            "WHERE llm_api_key_encrypted IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("users", "llm_litellm_key_encrypted")
    op.drop_column("users", "llm_anthropic_key_encrypted")
    op.drop_column("users", "llm_openai_key_encrypted")
    op.drop_column("users", "llm_litellm_base_url")
    op.drop_column("users", "llm_anthropic_base_url")
    op.drop_column("users", "llm_openai_base_url")
