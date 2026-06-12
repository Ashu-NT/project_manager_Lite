"""Add organization_id to time_entries with backfill via site_id and assignment chain.

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "v6w7x8y9z0a1"
down_revision = "u5v6w7x8y9z0"
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


def _first_scalar(connection: sa.Connection, sql: str) -> str | None:
    row = connection.execute(sa.text(sql)).first()
    if row is None:
        return None
    value = row[0]
    return str(value) if value else None


def _default_organization_id(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    if not _table_exists(inspector, "organizations"):
        return None
    columns = _column_names(inspector, "organizations")
    order_col = "created_at" if "created_at" in columns else "id"
    if "is_active" in columns:
        active = _first_scalar(
            connection,
            f"SELECT id FROM organizations WHERE is_active = 1 ORDER BY {order_col} LIMIT 1",
        )
        if active:
            return active
    return _first_scalar(connection, f"SELECT id FROM organizations ORDER BY {order_col} LIMIT 1")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not _table_exists(inspector, "time_entries"):
        return

    columns = _column_names(inspector, "time_entries")
    if "organization_id" not in columns:
        op.add_column("time_entries", sa.Column("organization_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    # Backfill from site_id -> sites.organization_id
    if _table_exists(inspector, "sites"):
        connection.execute(
            sa.text(
                """
                UPDATE time_entries
                   SET organization_id = (
                       SELECT sites.organization_id
                         FROM sites
                        WHERE sites.id = time_entries.site_id
                          AND sites.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND site_id IS NOT NULL
                """
            )
        )

    # Backfill via assignment -> task -> project -> organization_id
    if (
        _table_exists(inspector, "task_assignments")
        and _table_exists(inspector, "tasks")
        and _table_exists(inspector, "projects")
        and "organization_id" in _column_names(inspector, "projects")
    ):
        connection.execute(
            sa.text(
                """
                UPDATE time_entries
                   SET organization_id = (
                       SELECT projects.organization_id
                         FROM task_assignments
                         JOIN tasks ON tasks.id = task_assignments.task_id
                         JOIN projects ON projects.id = tasks.project_id
                        WHERE task_assignments.id = time_entries.assignment_id
                          AND projects.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND assignment_id IS NOT NULL
                """
            )
        )

    # Remaining entries get the default org
    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                "UPDATE time_entries SET organization_id = :org_id "
                "WHERE organization_id IS NULL OR organization_id = ''"
            ),
            {"org_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_time_entries_organization" not in _index_names(inspector, "time_entries"):
        op.create_index("idx_time_entries_organization", "time_entries", ["organization_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "time_entries"):
        return
    if "idx_time_entries_organization" in _index_names(inspector, "time_entries"):
        op.drop_index("idx_time_entries_organization", table_name="time_entries")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "time_entries"):
        with op.batch_alter_table("time_entries") as batch_op:
            batch_op.drop_column("organization_id")
