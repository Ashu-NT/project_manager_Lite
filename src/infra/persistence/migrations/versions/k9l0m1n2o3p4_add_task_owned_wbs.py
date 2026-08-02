"""add task-owned WBS hierarchy

Revision ID: k9l0m1n2o3p4
Revises: j8k9l0m1n2o3
Create Date: 2026-08-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "k9l0m1n2o3p4"
down_revision = "j8k9l0m1n2o3"
branch_labels = None
depends_on = None


def _backfill_root_wbs(bind) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT id, project_id FROM tasks "
            "ORDER BY project_id, start_date, task_code, name, id"
        )
    ).mappings()
    sequence_by_project: dict[str, int] = {}
    update_task = sa.text(
        "UPDATE tasks SET wbs_code = :wbs_code, sort_order = :sort_order "
        "WHERE id = :task_id"
    )
    for row in rows:
        project_id = str(row["project_id"])
        sequence = sequence_by_project.get(project_id, 0) + 1
        sequence_by_project[project_id] = sequence
        bind.execute(
            update_task,
            {
                "task_id": row["id"],
                "wbs_code": str(sequence),
                "sort_order": sequence - 1,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("parent_task_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("wbs_code", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0")
        )

    _backfill_root_wbs(bind)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("wbs_code", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("sort_order", existing_type=sa.Integer(), nullable=False)
        batch_op.create_check_constraint(
            "ck_tasks_wbs_parent_not_self",
            "parent_task_id IS NULL OR parent_task_id <> id",
        )
        batch_op.create_check_constraint("ck_tasks_wbs_sort_order", "sort_order >= 0")
        batch_op.create_check_constraint(
            "ck_tasks_wbs_code_length",
            "length(wbs_code) >= 1 AND length(wbs_code) <= 64",
        )
        batch_op.create_unique_constraint("uq_tasks_project_id", ["project_id", "id"])
        batch_op.create_unique_constraint(
            "uq_tasks_project_wbs_code",
            ["project_id", "wbs_code"],
        )
        batch_op.create_foreign_key(
            "fk_tasks_wbs_same_project_parent",
            "tasks",
            ["project_id", "parent_task_id"],
            ["project_id", "id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "idx_tasks_wbs_parent_order",
            ["project_id", "parent_task_id", "sort_order"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("idx_tasks_wbs_parent_order")
        batch_op.drop_constraint("fk_tasks_wbs_same_project_parent", type_="foreignkey")
        batch_op.drop_constraint("uq_tasks_project_wbs_code", type_="unique")
        batch_op.drop_constraint("uq_tasks_project_id", type_="unique")
        batch_op.drop_constraint("ck_tasks_wbs_sort_order", type_="check")
        batch_op.drop_constraint("ck_tasks_wbs_code_length", type_="check")
        batch_op.drop_constraint("ck_tasks_wbs_parent_not_self", type_="check")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("wbs_code")
        batch_op.drop_column("parent_task_id")
