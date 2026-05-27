"""add maintenance work request source lineage

Revision ID: b1c2d3e4f5a6
Revises: a1f2b3c4d5e6
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "a1f2b3c4d5e6"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def upgrade() -> None:
    if not _has_table("maintenance_work_requests"):
        return
    with op.batch_alter_table("maintenance_work_requests") as batch:
        if not _has_column("maintenance_work_requests", "source_id"):
            batch.add_column(sa.Column("source_id", sa.String(), nullable=True))
        if not _has_column("maintenance_work_requests", "source_plan_task_ids_json"):
            batch.add_column(sa.Column("source_plan_task_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if not _has_table("maintenance_work_requests"):
        return
    with op.batch_alter_table("maintenance_work_requests") as batch:
        if _has_column("maintenance_work_requests", "source_plan_task_ids_json"):
            batch.drop_column("source_plan_task_ids_json")
        if _has_column("maintenance_work_requests", "source_id"):
            batch.drop_column("source_id")
