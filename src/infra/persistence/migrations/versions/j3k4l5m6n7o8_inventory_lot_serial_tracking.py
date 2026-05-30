"""Inventory lot/serial lifecycle tracking and maintenance blackout calendar

Adds:
  - inventory_stock_transactions: lot_number, serial_number columns
  - maintenance_preventive_blackout_windows: new table

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "j3k4l5m6n7o8"
down_revision = "i2j3k4l5m6n7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Inventory: lot/serial tracking in stock transactions ─────────────────
    op.add_column(
        "inventory_stock_transactions",
        sa.Column("lot_number", sa.String(128), nullable=True),
    )
    op.add_column(
        "inventory_stock_transactions",
        sa.Column("serial_number", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_inv_transactions_lot",
        "inventory_stock_transactions",
        ["lot_number"],
        unique=False,
    )
    op.create_index(
        "ix_inv_transactions_serial",
        "inventory_stock_transactions",
        ["serial_number"],
        unique=False,
    )

    # ── Maintenance: preventive plan blackout windows ────────────────────────
    op.create_table(
        "maintenance_preventive_blackout_windows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column(
            "preventive_plan_id",
            sa.String(),
            sa.ForeignKey("maintenance_preventive_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("recurrence", sa.String(32), nullable=True),  # NONE | ANNUAL
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True, server_default="1"),
        sa.Column("version", sa.Integer(), nullable=False, default=1, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maint_blackout_plan_id",
        "maintenance_preventive_blackout_windows",
        ["preventive_plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_maint_blackout_plan_id", "maintenance_preventive_blackout_windows")
    op.drop_table("maintenance_preventive_blackout_windows")
    op.drop_index("ix_inv_transactions_serial", "inventory_stock_transactions")
    op.drop_index("ix_inv_transactions_lot", "inventory_stock_transactions")
    op.drop_column("inventory_stock_transactions", "serial_number")
    op.drop_column("inventory_stock_transactions", "lot_number")
