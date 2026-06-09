"""Add direct tenant ownership to PM resources.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-06-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


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
    order_column = "created_at" if "created_at" in columns else "id"
    if "is_active" in columns:
        active = _first_scalar(
            connection,
            f"SELECT id FROM organizations WHERE is_active = 1 ORDER BY {order_column} LIMIT 1",
        )
        if active:
            return active
    return _first_scalar(
        connection,
        f"SELECT id FROM organizations ORDER BY {order_column} LIMIT 1",
    )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "resources"):
        return

    columns = _column_names(inspector, "resources")
    if "organization_id" not in columns:
        op.add_column(
            "resources",
            sa.Column("organization_id", sa.String(), nullable=True),
        )
        inspector = sa.inspect(connection)
        columns = _column_names(inspector, "resources")

    # Backfill from project membership: derive org from a project this resource is assigned to.
    if "organization_id" in columns and _table_exists(inspector, "project_resources") and _table_exists(inspector, "projects"):
        connection.execute(
            sa.text(
                """
                UPDATE resources
                   SET organization_id = (
                       SELECT projects.organization_id
                         FROM project_resources
                         JOIN projects ON projects.id = project_resources.project_id
                        WHERE project_resources.resource_id = resources.id
                          AND projects.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE organization_id IS NULL OR organization_id = ''
                """
            )
        )

    # Backfill from employee site/department ownership.
    if "organization_id" in columns and _table_exists(inspector, "employees") and _table_exists(inspector, "sites"):
        connection.execute(
            sa.text(
                """
                UPDATE resources
                   SET organization_id = (
                       SELECT sites.organization_id
                         FROM employees
                         JOIN sites ON sites.id = employees.site_id
                        WHERE employees.id = resources.employee_id
                          AND sites.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND employee_id IS NOT NULL
                """
            )
        )

    # Remaining resources without any deterministic owner get the default org.
    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                """
                UPDATE resources
                   SET organization_id = :organization_id
                 WHERE organization_id IS NULL
                    OR organization_id = ''
                """
            ),
            {"organization_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_resources_organization" not in _index_names(inspector, "resources"):
        op.create_index(
            "idx_resources_organization",
            "resources",
            ["organization_id"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "resources"):
        return
    if "idx_resources_organization" in _index_names(inspector, "resources"):
        op.drop_index("idx_resources_organization", table_name="resources")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "resources"):
        with op.batch_alter_table("resources") as batch_op:
            batch_op.drop_column("organization_id")
