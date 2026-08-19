"""Add an explicit is_milestone flag to tasks.

Milestone detection was previously implicit and inconsistent: CPM treats
any task with duration_days <= 0 as a milestone, while
dashboard/widgets/professional.py's _is_explicit_milestone additionally
sniffs the task name for "milestone"/"gate". There was no dedicated
concept a user could set, view, or filter on directly. This migration
adds a real is_milestone column as the single source of truth; the
duration-guessing consumers are repointed to read it instead of
re-deriving it (see docs/pm_modernization/R4_4_TASK_DEPENDENCY_IMPLEMENTATION_SUMMARY.md,
"Milestones").

Backfill: existing rows with duration_days = 0 are marked is_milestone
so already-recognized milestones (per CPM's own convention) keep
displaying as one after this migration -- no manual re-tagging needed.
The name-sniffing heuristic is deliberately NOT used for backfill (too
unreliable a signal to write into persisted data).

Revision ID: x4y5z6a7b8c9
Revises: k3i9kex13spt
Create Date: 2026-08-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "x4y5z6a7b8c9"
down_revision = "k3i9kex13spt"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("tasks", "is_milestone"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_milestone",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )
        tasks = sa.table(
            "tasks",
            sa.column("is_milestone", sa.Boolean()),
            sa.column("duration_days", sa.Integer()),
        )
        op.execute(tasks.update().where(tasks.c.duration_days == 0).values(is_milestone=True))


def downgrade() -> None:
    if _has_column("tasks", "is_milestone"):
        with op.batch_alter_table("tasks", schema=None) as batch_op:
            batch_op.drop_column("is_milestone")
