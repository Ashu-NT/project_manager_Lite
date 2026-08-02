"""add user_id link to employees

Links an Employee record to a real platform UserAccount so features that
need to notify "the person behind this employee/resource" (e.g. PM task
assignment notifications) have a resolvable recipient. Nullable — not every
employee has (or needs) a login account.

Revision ID: 4f20c1d95e8f
Revises: 158ac9c0e0de
Create Date: 2026-08-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4f20c1d95e8f"
down_revision = "158ac9c0e0de"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "employees"):
        return

    if "user_id" not in _column_names(inspector, "employees"):
        op.add_column("employees", sa.Column("user_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    if "idx_employees_user" not in _index_names(inspector, "employees"):
        op.create_index("idx_employees_user", "employees", ["user_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "employees"):
        return
    if "idx_employees_user" in _index_names(inspector, "employees"):
        op.drop_index("idx_employees_user", table_name="employees")
    inspector = sa.inspect(connection)
    if "user_id" in _column_names(inspector, "employees"):
        with op.batch_alter_table("employees") as batch_op:
            batch_op.drop_column("user_id")
