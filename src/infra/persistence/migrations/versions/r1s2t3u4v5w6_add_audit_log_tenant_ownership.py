"""Add tenant ownership to audit logs (merges duplicate portfolio branch).

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5, t3u4v5w6x7y8
Create Date: 2026-06-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "r1s2t3u4v5w6"
down_revision = ("q0r1s2t3u4v5", "t3u4v5w6x7y8")
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
    if not _table_exists(inspector, "audit_logs"):
        return

    columns = _column_names(inspector, "audit_logs")
    if "organization_id" not in columns:
        op.add_column(
            "audit_logs",
            sa.Column("organization_id", sa.String(), nullable=True),
        )
        inspector = sa.inspect(connection)
        columns = _column_names(inspector, "audit_logs")

    # Backfill from project ownership where possible.
    if "organization_id" in columns and _table_exists(inspector, "projects"):
        connection.execute(
            sa.text(
                """
                UPDATE audit_logs
                   SET organization_id = (
                       SELECT projects.organization_id
                         FROM projects
                        WHERE projects.id = audit_logs.project_id
                   )
                 WHERE (organization_id IS NULL OR organization_id = '')
                   AND project_id IS NOT NULL
                """
            )
        )

    # Remaining entries with no project link get the default org as a safe fallback.
    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                """
                UPDATE audit_logs
                   SET organization_id = :organization_id
                 WHERE organization_id IS NULL
                    OR organization_id = ''
                """
            ),
            {"organization_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_audit_logs_organization_occurred" not in _index_names(inspector, "audit_logs"):
        op.create_index(
            "idx_audit_logs_organization_occurred",
            "audit_logs",
            ["organization_id", "occurred_at"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "audit_logs"):
        return
    if "idx_audit_logs_organization_occurred" in _index_names(inspector, "audit_logs"):
        op.drop_index("idx_audit_logs_organization_occurred", table_name="audit_logs")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "audit_logs"):
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.drop_column("organization_id")
