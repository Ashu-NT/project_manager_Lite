"""Add one-time tenant-membership invitation token hashes.

Revision ID: 7a2b3c4d5e6f
Revises: 6f1a9c2e8d4b
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "7a2b3c4d5e6f"
down_revision = "6f1a9c2e8d4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.add_column(
            sa.Column(
                "invitation_token_hash",
                sa.String(length=64),
                nullable=True,
            )
        )

    # Invitations created before token support cannot be securely accepted.
    op.execute(
        sa.text(
            "UPDATE user_tenants "
            "SET status = 'removed', "
            "revoked_at = COALESCE(revoked_at, updated_at, created_at), "
            "removed_at = COALESCE(removed_at, updated_at, created_at) "
            "WHERE status = 'invited'"
        )
    )

    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.create_check_constraint(
            "ck_user_tenants_invitation_token_state",
            "(status = 'invited' AND invitation_token_hash IS NOT NULL) OR "
            "(status <> 'invited' AND invitation_token_hash IS NULL)",
        )

    op.create_index(
        "ux_user_tenants_invitation_token_hash",
        "user_tenants",
        ["invitation_token_hash"],
        unique=True,
        sqlite_where=sa.text("invitation_token_hash IS NOT NULL"),
        postgresql_where=sa.text("invitation_token_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_user_tenants_invitation_token_hash",
        table_name="user_tenants",
    )
    with op.batch_alter_table("user_tenants") as batch_op:
        batch_op.drop_constraint(
            "ck_user_tenants_invitation_token_state",
            type_="check",
        )
        batch_op.drop_column("invitation_token_hash")
