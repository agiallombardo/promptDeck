"""Add Entra identity fields and presentation members.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


USER_ROLE_ENUM = sa.Enum("admin", "user", name="userrole", native_enum=False)
AUTH_PROVIDER_ENUM = sa.Enum("local", "entra", name="authprovider", native_enum=False)
MEMBER_ROLE_ENUM = sa.Enum("editor", "user", name="presentationmemberrole", native_enum=False)


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("auth_provider", AUTH_PROVIDER_ENUM, nullable=True))
        batch_op.add_column(sa.Column("entra_tenant_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("entra_object_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("entra_user_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("entra_refresh_token_encrypted", sa.Text(), nullable=True))

    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")
    op.execute("UPDATE users SET role = 'user' WHERE role IN ('editor', 'commenter', 'viewer')")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("auth_provider", nullable=False)
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "role",
            existing_type=sa.String(length=16),
            type_=USER_ROLE_ENUM,
            nullable=False,
        )
        batch_op.create_index(
            "ix_users_entra_identity",
            ["entra_tenant_id", "entra_object_id"],
            unique=True,
        )

    op.create_table(
        "presentation_members",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("presentation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", MEMBER_ROLE_ENUM, nullable=False),
        sa.Column("principal_tenant_id", sa.String(length=64), nullable=False),
        sa.Column("principal_entra_object_id", sa.String(length=64), nullable=False),
        sa.Column("principal_email", sa.String(length=320), nullable=False),
        sa.Column("principal_display_name", sa.String(length=200), nullable=True),
        sa.Column("principal_user_type", sa.String(length=32), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("granted_by", sa.Uuid(as_uuid=True), nullable=False),
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
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["presentation_id"], ["presentations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_presentation_members_identity",
        "presentation_members",
        ["presentation_id", "principal_tenant_id", "principal_entra_object_id"],
        unique=True,
    )
    op.create_index(
        "ix_presentation_members_user_id",
        "presentation_members",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_presentation_members_user_id", table_name="presentation_members")
    op.drop_index("ix_presentation_members_identity", table_name="presentation_members")
    op.drop_table("presentation_members")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_entra_identity")
        batch_op.alter_column(
            "role",
            existing_type=sa.String(length=16),
            type_=sa.Enum(
                "admin",
                "editor",
                "commenter",
                "viewer",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        )
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            nullable=False,
        )
        batch_op.drop_column("entra_refresh_token_encrypted")
        batch_op.drop_column("entra_user_type")
        batch_op.drop_column("entra_object_id")
        batch_op.drop_column("entra_tenant_id")
        batch_op.drop_column("auth_provider")
