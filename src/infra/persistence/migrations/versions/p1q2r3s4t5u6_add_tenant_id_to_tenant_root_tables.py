"""Add tenant_id to all tenant-root tables; backfill via organizations.tenant_id.

Covers: sites, departments, employees, parties, approval_requests, audit_logs,
document_structures, documents, platform_calendars, shift_patterns, projects,
resources, portfolio_scoring_templates, portfolio_intake_items, portfolio_scenarios,
time_entries, timesheet_periods, inventory (8 tables), maintenance (12 tables).

Revision ID: p1q2r3s4t5u6
Revises: z0a1b2c3d4e5
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "p1q2r3s4t5u6"
down_revision = "z0a1b2c3d4e5"
branch_labels = None
depends_on = None

# Every table listed here already has an organization_id column.
# tenant_id will be backfilled as:
#   UPDATE <table> SET tenant_id = (
#       SELECT o.tenant_id FROM organizations o WHERE o.id = <table>.organization_id
#   )
_TENANT_ROOT_TABLES = [
    "sites",
    "departments",
    "employees",
    "parties",
    "approval_requests",
    "audit_logs",
    "document_structures",
    "documents",
    "platform_calendars",
    "shift_patterns",
    "projects",
    "resources",
    "portfolio_scoring_templates",
    "portfolio_intake_items",
    "portfolio_scenarios",
    "time_entries",
    "timesheet_periods",
    "inventory_item_categories",
    "inventory_stock_items",
    "inventory_storerooms",
    "inventory_stock_balances",
    "inventory_stock_transactions",
    "inventory_stock_reservations",
    "inventory_purchase_requisitions",
    "inventory_purchase_orders",
    "inventory_receipt_headers",
    "maintenance_locations",
    "maintenance_systems",
    "maintenance_assets",
    "maintenance_sensors",
    "maintenance_work_requests",
    "maintenance_work_orders",
    "maintenance_preventive_plans",
]


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


def _default_tenant_id(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    if not _table_exists(inspector, "tenants"):
        return None
    return _first_scalar(connection, "SELECT id FROM tenants WHERE is_active = 1 ORDER BY tenant_code LIMIT 1")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    default_tenant_id = _default_tenant_id(connection, inspector)

    for table in _TENANT_ROOT_TABLES:
        if not _table_exists(inspector, table):
            continue
        columns = _column_names(inspector, table)
        if "tenant_id" not in columns:
            op.add_column(table, sa.Column("tenant_id", sa.String(), nullable=True))
            inspector = sa.inspect(connection)

        # Backfill from organization_id → organizations.tenant_id
        if "organization_id" in _column_names(inspector, table):
            connection.execute(
                sa.text(
                    f"""
                    UPDATE {table}
                       SET tenant_id = (
                           SELECT o.tenant_id
                             FROM organizations o
                            WHERE o.id = {table}.organization_id
                              AND o.tenant_id IS NOT NULL
                            LIMIT 1
                       )
                     WHERE (tenant_id IS NULL OR tenant_id = '')
                       AND organization_id IS NOT NULL
                    """
                )
            )

        # Remaining rows get the default tenant
        if default_tenant_id:
            connection.execute(
                sa.text(
                    f"UPDATE {table} SET tenant_id = :tid "
                    f"WHERE tenant_id IS NULL OR tenant_id = ''"
                ),
                {"tid": default_tenant_id},
            )

        # Index
        inspector = sa.inspect(connection)
        idx_name = f"idx_{table}_tenant"
        if idx_name not in _index_names(inspector, table):
            op.create_index(idx_name, table, ["tenant_id"])

        inspector = sa.inspect(connection)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    for table in reversed(_TENANT_ROOT_TABLES):
        if not _table_exists(inspector, table):
            continue
        idx_name = f"idx_{table}_tenant"
        if idx_name in _index_names(inspector, table):
            op.drop_index(idx_name, table_name=table)
        inspector = sa.inspect(connection)
        if "tenant_id" in _column_names(inspector, table):
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_column("tenant_id")
        inspector = sa.inspect(connection)
