"""user LLM columns and system_settings for Entra OIDC overrides."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.add_column("users", sa.Column("llm_provider", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "llm_api_key_encrypted")
    op.drop_column("users", "llm_provider")
    op.drop_table("system_settings")
