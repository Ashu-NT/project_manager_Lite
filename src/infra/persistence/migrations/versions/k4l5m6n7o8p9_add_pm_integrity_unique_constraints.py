"""Project Management integrity: unique constraints for dependencies & assignments

Adds defense-in-depth uniqueness the application layer already enforces on new
writes:
  - task_dependencies: UNIQUE(predecessor_task_id, successor_task_id)
  - task_assignments:  UNIQUE(task_id, resource_id)

Pre-flight guard: refuses to run if duplicate rows already exist, pointing the
operator at the read-only health check (`python -m tools.pm_data_integrity_check`)
to detect and clean them first. Nothing is deleted automatically.

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-05-31
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "k4l5m6n7o8p9"
down_revision = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def _assert_clean(bind) -> None:
    dep_dups = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            " SELECT 1 FROM task_dependencies"
            " GROUP BY predecessor_task_id, successor_task_id HAVING COUNT(*) > 1)"
        )
    ).scalar()
    asg_dups = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            " SELECT 1 FROM task_assignments"
            " GROUP BY task_id, resource_id HAVING COUNT(*) > 1)"
        )
    ).scalar()
    if dep_dups or asg_dups:
        raise RuntimeError(
            "Cannot add PM uniqueness constraints: duplicate rows exist "
            f"(duplicate dependency pairs={dep_dups}, duplicate assignments={asg_dups}). "
            "Run `python -m tools.pm_data_integrity_check`, clean the findings, then retry."
        )


def upgrade() -> None:
    bind = op.get_bind()
    _assert_clean(bind)
    op.create_index(
        "ux_task_dependencies_pair",
        "task_dependencies",
        ["predecessor_task_id", "successor_task_id"],
        unique=True,
    )
    op.create_index(
        "ux_task_assignments_task_resource",
        "task_assignments",
        ["task_id", "resource_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_task_assignments_task_resource", table_name="task_assignments")
    op.drop_index("ux_task_dependencies_pair", table_name="task_dependencies")
