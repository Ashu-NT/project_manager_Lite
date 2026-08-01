"""add response_status/responded_at to task_assignments

Lets an assignee accept or decline a task handoff instead of only ever
being silently assigned. Existing rows default to "pending" so nothing
that reads/writes assignments today is gated by this new field.

Revision ID: 8b2c3d4e5f6a
Revises: 7a1b2c3d4e5f
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "8b2c3d4e5f6a"
down_revision = "7a1b2c3d4e5f"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "task_assignments"):
        return

    columns = _column_names(inspector, "task_assignments")

    if "response_status" not in columns:
        op.add_column(
            "task_assignments",
            sa.Column("response_status", sa.String(16), nullable=False, server_default="pending"),
        )

    if "responded_at" not in columns:
        op.add_column("task_assignments", sa.Column("responded_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "task_assignments"):
        return

    columns = _column_names(inspector, "task_assignments")
    with op.batch_alter_table("task_assignments") as batch_op:
        if "response_status" in columns:
            batch_op.drop_column("response_status")
        if "responded_at" in columns:
            batch_op.drop_column("responded_at")
