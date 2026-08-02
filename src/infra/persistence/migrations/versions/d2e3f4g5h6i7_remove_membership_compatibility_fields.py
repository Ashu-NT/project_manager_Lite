"""Remove non-authoritative tenant membership compatibility fields.

Revision ID: d2e3f4g5h6i7
Revises: 8b2c3d4e5f6a

Membership admission is represented exclusively by the lifecycle `status` column.
Tenant authority is represented exclusively by canonical `role_bindings`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4g5h6i7"
down_revision = "8b2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_user_tenants_active", table_name="user_tenants")
    with op.batch_alter_table("user_tenants", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_user_tenants_active_status", type_="check")
        batch_op.drop_column("tenant_role")
        batch_op.drop_column("is_active")


def downgrade() -> None:
    with op.batch_alter_table("user_tenants", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "tenant_role",
                sa.String(length=64),
                nullable=False,
                server_default="member",
            )
        )

    op.execute(
        sa.text(
            "UPDATE user_tenants "
            "SET is_active = CASE WHEN status = 'active' THEN true ELSE false END"
        )
    )
    with op.batch_alter_table("user_tenants", recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_user_tenants_active_status",
            "(status = 'active' AND is_active) OR "
            "(status <> 'active' AND NOT is_active)",
        )
    op.create_index("idx_user_tenants_active", "user_tenants", ["is_active"])
