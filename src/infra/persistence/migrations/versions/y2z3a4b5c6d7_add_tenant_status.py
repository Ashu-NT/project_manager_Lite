"""Add tenant_status column to tenants table.

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-06-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "y2z3a4b5c6d7"
down_revision = "x1y2z3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tenants") as batch_op:
        batch_op.add_column(
            sa.Column(
                "tenant_status",
                sa.String(32),
                nullable=False,
                server_default="active",
            )
        )

    # Backfill: rows with is_active=0 become "suspended" (reversible — not discarded).
    # Rows with is_active=1 are already covered by the server_default "active".
    op.execute("UPDATE tenants SET tenant_status = 'suspended' WHERE is_active = 0")
    op.execute("UPDATE tenants SET tenant_status = 'active'    WHERE is_active = 1")


def downgrade() -> None:
    with op.batch_alter_table("tenants") as batch_op:
        batch_op.drop_column("tenant_status")
