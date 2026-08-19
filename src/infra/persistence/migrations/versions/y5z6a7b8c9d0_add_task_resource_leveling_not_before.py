"""Add Task.resource_leveling_not_before (R4.4 resource-leveling migration).

The pre-R4.4 architecture had resource leveling write its decision
directly onto Task.start_date/end_date. That decision was silently
erased the very next time the canonical schedule was recalculated,
because run_cpm ignores a task's own persisted start_date whenever it
has a usable incoming dependency (see
src/tests/project_management/dependency/test_leveling_dependency_boundary.py,
the pinned regression this migration's forward-CPM integration
resolves).

This migration adds a new, distinct not-before boundary a resource
leveling decision can occupy -- separate from Task.constraint_type/
constraint_date, which represent a USER's own explicit scheduling
instruction, not a scheduler-generated placement. The forward CPM pass
applies this floor unconditionally (task_date_math.
apply_resource_leveling_floor), exactly like START_NO_EARLIER_THAN, so
an accepted leveling placement survives every subsequent canonical
run_cpm call, dependency or not.

No backfill: every existing task's resource leveling state is NULL
(unset) after this migration -- there is no reliable way to infer a
historical leveling decision from Task.start_date alone (that ambiguity
is exactly the defect this field exists to remove), so nothing is
backfilled.

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-08-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "y5z6a7b8c9d0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("tasks", "resource_leveling_not_before"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("resource_leveling_not_before", sa.Date(), nullable=True)
            )


def downgrade() -> None:
    if _has_column("tasks", "resource_leveling_not_before"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.drop_column("resource_leveling_not_before")
