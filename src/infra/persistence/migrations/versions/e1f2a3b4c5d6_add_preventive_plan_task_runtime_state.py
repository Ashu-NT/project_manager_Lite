"""add preventive plan task runtime state

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-04-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("maintenance_preventive_plan_tasks") as batch:
        batch.add_column(sa.Column("last_generated_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("next_due_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("next_due_counter", sa.Numeric(18, 6), nullable=True))
    op.create_index(
        "idx_maintenance_plan_tasks_next_due_at",
        "maintenance_preventive_plan_tasks",
        ["next_due_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_maintenance_plan_tasks_next_due_at", table_name="maintenance_preventive_plan_tasks")
    with op.batch_alter_table("maintenance_preventive_plan_tasks") as batch:
        batch.drop_column("next_due_counter")
        batch.drop_column("next_due_at")
        batch.drop_column("last_generated_at")
