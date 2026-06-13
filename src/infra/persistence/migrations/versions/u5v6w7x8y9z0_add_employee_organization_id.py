"""Add organization_id to employees with backfill from site and department.

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8z0
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "u5v6w7x8y9z0"
down_revision = "t4u5v6w7x8z0"
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

    if not _table_exists(inspector, "employees"):
        return

    columns = _column_names(inspector, "employees")
    if "organization_id" not in columns:
        op.add_column("employees", sa.Column("organization_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    # Backfill from site.organization_id
    if _table_exists(inspector, "sites"):
        connection.execute(
            sa.text(
                """
                UPDATE employees
                   SET organization_id = (
                       SELECT sites.organization_id
                         FROM sites
                        WHERE sites.id = employees.site_id
                          AND sites.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND site_id IS NOT NULL
                """
            )
        )

    # Backfill from department.organization_id for employees with no site
    if _table_exists(inspector, "departments"):
        connection.execute(
            sa.text(
                """
                UPDATE employees
                   SET organization_id = (
                       SELECT departments.organization_id
                         FROM departments
                        WHERE departments.id = employees.department_id
                          AND departments.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND department_id IS NOT NULL
                """
            )
        )

    # Remaining employees without site or department get the default org
    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                "UPDATE employees SET organization_id = :org_id "
                "WHERE organization_id IS NULL OR organization_id = ''"
            ),
            {"org_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_employees_organization" not in _index_names(inspector, "employees"):
        op.create_index("idx_employees_organization", "employees", ["organization_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "employees"):
        return
    if "idx_employees_organization" in _index_names(inspector, "employees"):
        op.drop_index("idx_employees_organization", table_name="employees")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "employees"):
        with op.batch_alter_table("employees") as batch_op:
            batch_op.drop_column("organization_id")
