"""enable PostgreSQL tenant row-level security

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-08-02
"""

from alembic import op
import sqlalchemy as sa


revision = "h6i7j8k9l0m1"
down_revision = "g5h6i7j8k9l0"
branch_labels = None
depends_on = None


TENANT_RLS_TABLES = (
    "activity_entries",
    "approval_requests",
    "departments",
    "document_structures",
    "documents",
    "employees",
    "inventory_item_categories",
    "inventory_purchase_orders",
    "inventory_purchase_requisitions",
    "inventory_receipt_headers",
    "inventory_stock_balances",
    "inventory_stock_items",
    "inventory_stock_reservations",
    "inventory_stock_transactions",
    "inventory_storerooms",
    "maintenance_assets",
    "maintenance_locations",
    "maintenance_preventive_plans",
    "maintenance_sensors",
    "maintenance_systems",
    "maintenance_work_orders",
    "maintenance_work_requests",
    "organization_module_entitlements",
    "parties",
    "platform_calendars",
    "platform_events",
    "portfolio_intake_items",
    "portfolio_scenarios",
    "portfolio_scoring_templates",
    "projects",
    "resources",
    "runtime_executions",
    "service_principal_api_keys",
    "service_principals",
    "shift_patterns",
    "sites",
    "time_entries",
    "timesheet_periods",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    for table_name in TENANT_RLS_TABLES:
        if table_name not in existing:
            continue
        quoted = bind.dialect.identifier_preparer.quote(table_name)
        policy = bind.dialect.identifier_preparer.quote(
            f"{table_name}_tenant_isolation"
        )
        op.execute(sa.text(f"ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY {policy} ON {quoted} "
                "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')) "
                "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), ''))"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    for table_name in reversed(TENANT_RLS_TABLES):
        if table_name not in existing:
            continue
        quoted = bind.dialect.identifier_preparer.quote(table_name)
        policy = bind.dialect.identifier_preparer.quote(
            f"{table_name}_tenant_isolation"
        )
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {quoted}"))
        op.execute(sa.text(f"ALTER TABLE {quoted} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {quoted} DISABLE ROW LEVEL SECURITY"))


__all__ = ["TENANT_RLS_TABLES"]
