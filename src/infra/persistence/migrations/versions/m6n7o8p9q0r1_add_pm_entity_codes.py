"""Project Management: human-readable codes for task / resource / cost / register

Adds nullable code columns, backfills deterministic name-token codes (scoped:
task/cost/register per-project, resource global), then adds unique indexes.
Reversible. See docs/PM_CODE_FIELDS_MIGRATION_PLAN.md.

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m6n7o8p9q0r1"
down_revision = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def _backfill(bind, table, code_col, name_col, prefix, *, per_project):
    from src.core.platform.common.code_generation import generate_unique_code, sanitize_token

    scope_sql = "project_id, " if per_project else ""
    rows = bind.execute(
        sa.text(f"SELECT id, {scope_sql}{name_col} FROM {table} ORDER BY {scope_sql}id")
    ).fetchall()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        row_id = row[0]
        scope = (row[1] if per_project else "") or ""
        name = (row[2] if per_project else row[1]) or ""
        code = generate_unique_code(
            prefix,
            exists=lambda candidate: (scope, candidate) in seen,
            segment=sanitize_token(name),
        )
        seen.add((scope, code))
        bind.execute(
            sa.text(f"UPDATE {table} SET {code_col} = :code WHERE id = :id"),
            {"code": code, "id": row_id},
        )


def upgrade() -> None:
    op.add_column("tasks", sa.Column("task_code", sa.String(64), nullable=True))
    op.add_column("resources", sa.Column("resource_code", sa.String(64), nullable=True))
    op.add_column("cost_items", sa.Column("cost_code", sa.String(64), nullable=True))
    op.add_column("register_entries", sa.Column("entry_code", sa.String(64), nullable=True))

    bind = op.get_bind()
    _backfill(bind, "tasks", "task_code", "name", "TSK", per_project=True)
    _backfill(bind, "resources", "resource_code", "name", "RES", per_project=False)
    _backfill(bind, "cost_items", "cost_code", "description", "CST", per_project=True)
    _backfill(bind, "register_entries", "entry_code", "title", "REG", per_project=True)

    op.create_index("ux_tasks_project_code", "tasks", ["project_id", "task_code"], unique=True)
    op.create_index("ux_resources_code", "resources", ["resource_code"], unique=True)
    op.create_index("ux_costs_project_code", "cost_items", ["project_id", "cost_code"], unique=True)
    op.create_index(
        "ux_register_entries_project_code",
        "register_entries",
        ["project_id", "entry_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_register_entries_project_code", table_name="register_entries")
    op.drop_index("ux_costs_project_code", table_name="cost_items")
    op.drop_index("ux_resources_code", table_name="resources")
    op.drop_index("ux_tasks_project_code", table_name="tasks")
    op.drop_column("register_entries", "entry_code")
    op.drop_column("cost_items", "cost_code")
    op.drop_column("resources", "resource_code")
    op.drop_column("tasks", "task_code")
