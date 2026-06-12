"""Add tenant ownership to approval requests.

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
Create Date: 2026-06-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
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
    if not _table_exists(inspector, "approval_requests"):
        return

    columns = _column_names(inspector, "approval_requests")
    if "organization_id" not in columns:
        op.add_column(
            "approval_requests",
            sa.Column("organization_id", sa.String(), nullable=True),
        )
        inspector = sa.inspect(connection)
        columns = _column_names(inspector, "approval_requests")

    if "organization_id" in columns and _table_exists(inspector, "projects"):
        connection.execute(
            sa.text(
                """
                UPDATE approval_requests
                   SET organization_id = (
                       SELECT projects.organization_id
                         FROM projects
                        WHERE projects.id = approval_requests.project_id
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND project_id IS NOT NULL
                """
            )
        )

    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                """
                UPDATE approval_requests
                   SET organization_id = :organization_id
                 WHERE organization_id IS NULL
                    OR organization_id = ''
                """
            ),
            {"organization_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_approval_organization_status" not in _index_names(inspector, "approval_requests"):
        op.create_index(
            "idx_approval_organization_status",
            "approval_requests",
            ["organization_id", "status"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "approval_requests"):
        return
    if "idx_approval_organization_status" in _index_names(inspector, "approval_requests"):
        op.drop_index("idx_approval_organization_status", table_name="approval_requests")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "approval_requests"):
        with op.batch_alter_table("approval_requests") as batch_op:
            batch_op.drop_column("organization_id")
