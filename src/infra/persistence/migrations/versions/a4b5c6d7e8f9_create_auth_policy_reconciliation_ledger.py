"""Create the append-only authorization policy reconciliation ledger."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a4b5c6d7e8f9"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_policy_reconciliations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("change_set_hash", sa.String(length=64), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.Column("applied_by_user_id", sa.String(), nullable=False),
        sa.Column("rollback_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_name",
            "to_version",
            name="ux_auth_policy_reconciliation_version",
        ),
    )
    op.create_index(
        "ix_auth_policy_reconciliations_policy_name",
        "auth_policy_reconciliations",
        ["policy_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_policy_reconciliations_policy_name",
        table_name="auth_policy_reconciliations",
    )
    op.drop_table("auth_policy_reconciliations")
