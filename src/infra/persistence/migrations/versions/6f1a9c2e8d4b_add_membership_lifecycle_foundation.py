"""Add explicit tenant-membership lifecycle metadata.

Revision ID: 6f1a9c2e8d4b
Revises: b5c6d7e8f9a0
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "6f1a9c2e8d4b"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="active",
            )
        )
        batch_op.add_column(
            sa.Column("invited_by_user_id", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("invitation_expires_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("accepted_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("suspended_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("revoked_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("removed_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_foreign_key(
            "fk_user_tenants_invited_by_user_id_users",
            "users",
            ["invited_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        sa.text(
            "UPDATE user_tenants "
            "SET status = CASE "
            "WHEN is_active THEN 'active' ELSE 'suspended' END, "
            "accepted_at = COALESCE(joined_at, created_at), "
            "suspended_at = CASE "
            "WHEN is_active THEN NULL ELSE COALESCE(updated_at, created_at) END, "
            "version = 1"
        )
    )

    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.create_check_constraint(
            "ck_user_tenants_status",
            "status IN ('invited', 'active', 'suspended', 'removed')",
        )
        batch_op.create_check_constraint(
            "ck_user_tenants_active_status",
            "(status = 'active' AND is_active) OR "
            "(status <> 'active' AND NOT is_active)",
        )
        batch_op.create_check_constraint(
            "ck_user_tenants_version_positive",
            "version >= 1",
        )

    op.create_index(
        "idx_user_tenants_status",
        "user_tenants",
        ["status"],
    )
    op.create_index(
        "idx_user_tenants_invitation_expiry",
        "user_tenants",
        ["invitation_expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_user_tenants_invitation_expiry",
        table_name="user_tenants",
    )
    op.drop_index("idx_user_tenants_status", table_name="user_tenants")

    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.drop_constraint(
            "ck_user_tenants_version_positive",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_user_tenants_active_status",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_user_tenants_status",
            type_="check",
        )
        batch_op.drop_constraint(
            "fk_user_tenants_invited_by_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("version")
        batch_op.drop_column("removed_at")
        batch_op.drop_column("revoked_at")
        batch_op.drop_column("suspended_at")
        batch_op.drop_column("accepted_at")
        batch_op.drop_column("invitation_expires_at")
        batch_op.drop_column("invited_by_user_id")
        batch_op.drop_column("status")
