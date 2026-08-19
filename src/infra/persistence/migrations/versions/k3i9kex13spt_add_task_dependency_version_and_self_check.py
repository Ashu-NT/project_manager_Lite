"""Add optimistic-concurrency version and a self-dependency CHECK constraint
to task_dependencies.

TaskDependency had no version column at all -- unlike its sibling
aggregates Task (version, since the baseline) and TaskAssignment (version,
added alongside it) -- so concurrent edits to the same dependency silently
overwrote each other with no conflict detection, and a concurrent
double-delete could report success while deleting nothing. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§16/Phase G for the audit finding this closes.

Self-dependency (predecessor_task_id == successor_task_id) was previously
enforced only in the domain model and application layer -- never at the DB
level, unlike the analogous `ck_tasks_wbs_parent_not_self` constraint that
already exists on `tasks`. This migration adds the matching CHECK
constraint as defense-in-depth (§G4); it will refuse to apply if any
already-persisted self-dependency rows exist, the same fail-safe pattern
used by k4l5m6n7o8p9_add_pm_integrity_unique_constraints.py for the
duplicate-pair unique index.

Revision ID: k3i9kex13spt
Revises: a9f3e7c2b8d1
Create Date: 2026-08-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "k3i9kex13spt"
down_revision = "a9f3e7c2b8d1"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def _has_check_constraint(table: str, name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    try:
        return any(ck.get("name") == name for ck in insp.get_check_constraints(table))
    except NotImplementedError:  # pragma: no cover - some dialects can't introspect checks
        return False


def _assert_no_self_dependencies() -> None:
    conn = op.get_bind()
    bad = conn.execute(
        sa.text(
            "SELECT id FROM task_dependencies WHERE predecessor_task_id = successor_task_id LIMIT 1"
        )
    ).first()
    if bad is not None:
        raise RuntimeError(
            "Refusing to add ck_task_dependencies_not_self: at least one "
            "existing task_dependencies row has predecessor_task_id == "
            "successor_task_id (id="
            f"{bad[0]}). Run `python -m tools.pm_data_integrity_check` and "
            "resolve the offending row(s) before re-running this migration."
        )


def upgrade() -> None:
    if not _has_column("task_dependencies", "version"):
        with op.batch_alter_table("task_dependencies", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("version", sa.Integer(), nullable=False, server_default="1")
            )

    if not _has_check_constraint("task_dependencies", "ck_task_dependencies_not_self"):
        _assert_no_self_dependencies()
        with op.batch_alter_table("task_dependencies", schema=None) as batch_op:
            batch_op.create_check_constraint(
                "ck_task_dependencies_not_self",
                "predecessor_task_id <> successor_task_id",
            )


def downgrade() -> None:
    with op.batch_alter_table("task_dependencies", schema=None) as batch_op:
        if _has_check_constraint("task_dependencies", "ck_task_dependencies_not_self"):
            batch_op.drop_constraint("ck_task_dependencies_not_self", type_="check")
        if _has_column("task_dependencies", "version"):
            batch_op.drop_column("version")
