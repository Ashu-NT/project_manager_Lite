"""Add organization_id to timesheet_periods with backfill via resource.organization_id.

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "w7x8y9z0a1b2"
down_revision = "v6w7x8y9z0a1"
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

    if not _table_exists(inspector, "timesheet_periods"):
        return

    columns = _column_names(inspector, "timesheet_periods")
    if "organization_id" not in columns:
        op.add_column("timesheet_periods", sa.Column("organization_id", sa.String(), nullable=True))
        inspector = sa.inspect(connection)

    # Backfill via resource.organization_id
    if (
        _table_exists(inspector, "resources")
        and "organization_id" in _column_names(inspector, "resources")
    ):
        connection.execute(
            sa.text(
                """
                UPDATE timesheet_periods
                   SET organization_id = (
                       SELECT resources.organization_id
                         FROM resources
                        WHERE resources.id = timesheet_periods.resource_id
                          AND resources.organization_id IS NOT NULL
                        LIMIT 1
                   )
                 WHERE organization_id IS NULL OR organization_id = ''
                """
            )
        )

    # Remaining get the default org
    default_org_id = _default_organization_id(connection, inspector)
    if default_org_id:
        connection.execute(
            sa.text(
                "UPDATE timesheet_periods SET organization_id = :org_id "
                "WHERE organization_id IS NULL OR organization_id = ''"
            ),
            {"org_id": default_org_id},
        )

    inspector = sa.inspect(connection)
    if "idx_timesheet_periods_organization" not in _index_names(inspector, "timesheet_periods"):
        op.create_index("idx_timesheet_periods_organization", "timesheet_periods", ["organization_id"])


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not _table_exists(inspector, "timesheet_periods"):
        return
    if "idx_timesheet_periods_organization" in _index_names(inspector, "timesheet_periods"):
        op.drop_index("idx_timesheet_periods_organization", table_name="timesheet_periods")
    inspector = sa.inspect(connection)
    if "organization_id" in _column_names(inspector, "timesheet_periods"):
        with op.batch_alter_table("timesheet_periods") as batch_op:
            batch_op.drop_column("organization_id")
