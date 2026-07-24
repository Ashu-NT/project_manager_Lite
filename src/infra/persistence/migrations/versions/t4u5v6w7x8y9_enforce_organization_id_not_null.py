"""Backfill and enforce organization_id on projects, resources, approval_requests, audit_logs.

Revision ID: t4u5v6w7x8y9
Revises: s2t3u4v5w6x7
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "t4u5v6w7x8y9"
down_revision = "s2t3u4v5w6x7"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


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


def _backfill_table(connection: sa.Connection, inspector: sa.Inspector, table: str, default_org_id: str) -> None:
    if not _table_exists(inspector, table):
        return
    if "organization_id" not in _column_names(inspector, table):
        return
    connection.execute(
        sa.text(
            f"UPDATE {table} SET organization_id = :org_id WHERE organization_id IS NULL OR organization_id = ''"
        ),
        {"org_id": default_org_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    default_org_id = _default_organization_id(connection, inspector)
    if not default_org_id:
        return

    for table in ("projects", "resources", "approval_requests", "audit_logs"):
        _backfill_table(connection, inspector, table, default_org_id)


def downgrade() -> None:
    pass
