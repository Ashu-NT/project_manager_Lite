"""drop the obsolete combined project cost table

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "t7u8v9w0x1y2"
down_revision = "s6t7u8v9w0x1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("cost_items")


def downgrade() -> None:
    op.create_table(
        "cost_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("cost_code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("cost_type", sa.String(), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=True),
        sa.Column("planned_amount", sa.Float(), nullable=False),
        sa.Column("committed_amount", sa.Float(), nullable=True),
        sa.Column("actual_amount", sa.Float(), nullable=True),
        sa.Column("forecast_amount", sa.Float(), nullable=True),
        sa.Column("commitment_status", sa.String(length=20), server_default="uncommitted", nullable=False),
        sa.Column("vendor_reference", sa.String(), nullable=True),
        sa.Column("incurred_date", sa.Date(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_costs_project", "cost_items", ["project_id"])
    op.create_index("ux_costs_project_code", "cost_items", ["project_id", "cost_code"], unique=True)
    op.create_index("idx_costs_task", "cost_items", ["task_id"])
    op.create_index("idx_costs_type", "cost_items", ["cost_type"])
    op.create_index("idx_costs_commitment_status", "cost_items", ["commitment_status"])
