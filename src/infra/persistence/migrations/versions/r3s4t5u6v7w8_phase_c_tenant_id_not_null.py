"""Phase C: Make tenant_id NOT NULL on organizations and all 33 tenant_root tables.

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-06-12

All tenant_id columns were added as nullable in Phase B and backfilled from
organization → tenant. This migration hardens them to NOT NULL so the DB
enforces the invariant going forward.

SQLite cannot ALTER COLUMN nullability in-place. We use batch_alter_table
with recreate="always" which performs a full table copy under the hood.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None

# Tables with tenant_id to harden.
# Each entry: (table_name, existing_fk_target)
# organizations is first because the 33 tenant_root tables FK into it.
_TENANT_ROOT_TABLES = [
    "organizations",
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


def _table_has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def _count_nulls(table: str, column: str) -> int:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
    )
    return result.scalar() or 0


def _drop_tmp_table_if_exists(table: str) -> None:
    """Drop any leftover _alembic_tmp_ table from a previously interrupted batch migration."""
    bind = op.get_bind()
    bind.execute(sa.text(f"DROP TABLE IF EXISTS _alembic_tmp_{table}"))


def upgrade() -> None:
    for table in _TENANT_ROOT_TABLES:
        if not _table_has_column(table, "tenant_id"):
            # Phase B migration not yet applied — skip safely.
            continue

        null_count = _count_nulls(table, "tenant_id")
        if null_count > 0:
            raise RuntimeError(
                f"Cannot apply NOT NULL to {table}.tenant_id: "
                f"{null_count} rows still have NULL tenant_id. "
                "Run Phase B backfill migration first."
            )

        _drop_tmp_table_if_exists(table)
        with op.batch_alter_table(
            table, recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.alter_column(
                "tenant_id",
                existing_type=sa.String(),
                nullable=False,
            )


def downgrade() -> None:
    for table in reversed(_TENANT_ROOT_TABLES):
        if not _table_has_column(table, "tenant_id"):
            continue
        _drop_tmp_table_if_exists(table)
        with op.batch_alter_table(
            table, recreate="always", reflect_kwargs={"resolve_fks": False}
        ) as batch_op:
            batch_op.alter_column(
                "tenant_id",
                existing_type=sa.String(),
                nullable=True,
            )
