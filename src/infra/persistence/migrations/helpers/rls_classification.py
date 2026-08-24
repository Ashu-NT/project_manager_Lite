"""Authoritative PostgreSQL RLS classification for the fresh-schema baseline."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from .postgresql_rls import (
    disable_nullable_tenant_audit_rls,
    disable_tenant_only_rls,
    disable_tenant_organization_rls,
    enable_nullable_tenant_audit_rls,
    enable_tenant_only_rls,
    enable_tenant_organization_rls,
)


TENANT_AND_ORGANIZATION_TABLES = frozenset(
    {
        "activity_entries",
        "approval_requests",
        "departments",
        "document_structures",
        "documents",
        "employees",
        "financial_periods",
        "inventory_item_categories",
        "inventory_procurement_financial_outbox",
        "inventory_purchase_orders",
        "inventory_purchase_requisitions",
        "inventory_receipt_headers",
        "inventory_stock_balances",
        "inventory_stock_items",
        "inventory_stock_reservations",
        "inventory_stock_transactions",
        "inventory_storerooms",
        "organization_module_entitlements",
        "parties",
        "platform_calendars",
        "platform_time_financial_outbox",
        "portfolio_intake_items",
        "portfolio_scenarios",
        "portfolio_scoring_templates",
        "project_approved_time_labor_postings",
        "project_billing_external_events",
        "project_billing_preparation_lines",
        "project_billing_preparations",
        "project_billing_profiles",
        "project_billing_schedule_lines",
        "project_billing_source_locks",
        "project_commitment_lines",
        "project_commitment_matches",
        "project_commitment_source_revisions",
        "project_commitments",
        "project_cost_entries",
        "project_finance_cost_code_restrictions",
        "project_finance_cost_codes",
        "project_finance_budget_lines",
        "project_finance_budgets",
        "project_finance_change_impacts",
        "project_finance_change_requests",
        "project_finance_forecast_lines",
        "project_finance_forecast_source_decisions",
        "project_finance_forecasts",
        "project_finance_inbox_receipts",
        "project_finance_profiles",
        "project_finance_planned_cost_lines",
        "project_finance_planned_cost_versions",
        "project_finance_rate_card_lines",
        "project_finance_rate_cards",
        "projects",
        "resources",
        "runtime_executions",
        "service_principals",
        "shift_patterns",
        "sites",
        "time_entries",
        "timesheet_periods",
    }
)

TENANT_ONLY_TABLES = frozenset(
    {
        "platform_events",
        "service_principal_api_keys",
    }
)

NULLABLE_TENANT_AUDIT_TABLES = frozenset({"audit_entries"})

# These tables are intentionally outside direct RLS. Parent-scoped children are
# reachable only through repositories that join to an RLS-protected owner.
INTENTIONAL_RLS_EXCLUSIONS: Mapping[str, str] = {
    "auth_policy_reconciliations": "global authorization-policy reconciliation ledger",
    "auth_sessions": "user-owned authentication bootstrap state",
    "baseline_tasks": "project-baseline child scoped through project_baselines",
    "baseline_variance_records": "project-baseline child scoped through project_baselines",
    "calendar_exceptions": "calendar child scoped through platform_calendars",
    "calendar_recurring_events": "calendar child scoped through platform_calendars",
    "calendar_working_rules": "calendar child scoped through platform_calendars",
    "department_calendar_assignments": "calendar assignment scoped through department and calendar owners",
    "document_links": "document child scoped through documents",
    "employee_calendar_assignments": "calendar assignment scoped through employee and calendar owners",
    "inventory_cycle_counts": "inventory child scoped through an RLS-protected stock item",
    "inventory_purchase_order_lines": "purchase-order child scoped through inventory_purchase_orders",
    "inventory_purchase_requisition_lines": "requisition child scoped through inventory_purchase_requisitions",
    "inventory_receipt_lines": "receipt child scoped through inventory_receipt_headers",
    "inventory_reorder_policies": "inventory child scoped through an RLS-protected stock item",
    "inventory_storage_locations": "storeroom child scoped through inventory_storerooms",
    "notifications": "recipient-owned bootstrap data read before tenant context is established",
    "organizations": "tenant-context bootstrap root",
    "permissions": "global canonical permission catalog",
    "portfolio_project_dependencies": "portfolio child scoped through RLS-protected projects",
    "project_baselines": "project child scoped through RLS-protected projects",
    "project_calendar_assignments": "project/calendar association scoped through protected owners",
    "project_resources": "project/resource association scoped through protected owners",
    "register_entries": "project child scoped through RLS-protected projects",
    "resource_calendar_assignments": "resource/calendar association scoped through protected owners",
    "resource_certifications": "resource child scoped through RLS-protected resources",
    "resource_skills": "resource child scoped through RLS-protected resources",
    "role_bindings": "authorization bootstrap state used to establish tenant context",
    "role_delegation_policies": "authorization bootstrap state used to establish tenant context",
    "role_permissions": "role child scoped through the canonical role owner",
    "roles": "authorization bootstrap state used to establish tenant context",
    "shift_pattern_days": "shift-pattern child scoped through shift_patterns",
    "site_calendar_assignments": "site/calendar association scoped through protected owners",
    "task_assignments": "task child scoped through RLS-protected projects",
    "task_comments": "task child scoped through RLS-protected projects",
    "task_dependencies": "task child scoped through RLS-protected projects",
    "task_presence": "task child scoped through RLS-protected projects",
    "task_skill_requirements": "task child scoped through RLS-protected projects",
    "tasks": "project child scoped through RLS-protected projects",
    "tenants": "global tenant bootstrap root",
    "user_tenants": "membership bootstrap state used to establish tenant context",
    "users": "global identity bootstrap root",
}

INTENTIONAL_RLS_EXCLUSION_TABLES = frozenset(INTENTIONAL_RLS_EXCLUSIONS)
ALL_CLASSIFIED_TABLES = frozenset().union(
    TENANT_AND_ORGANIZATION_TABLES,
    TENANT_ONLY_TABLES,
    NULLABLE_TENANT_AUDIT_TABLES,
    INTENTIONAL_RLS_EXCLUSION_TABLES,
)


def validate_rls_classification(
    table_names: Collection[str],
    columns_by_table: Mapping[str, Collection[str]],
) -> None:
    """Fail closed when metadata and the reviewed RLS manifest diverge."""
    groups = (
        TENANT_AND_ORGANIZATION_TABLES,
        TENANT_ONLY_TABLES,
        NULLABLE_TENANT_AUDIT_TABLES,
        INTENTIONAL_RLS_EXCLUSION_TABLES,
    )
    for index, group in enumerate(groups):
        for other in groups[index + 1 :]:
            overlap = group & other
            if overlap:
                raise RuntimeError(f"RLS classifications overlap: {sorted(overlap)}")

    actual = frozenset(table_names)
    missing = actual - ALL_CLASSIFIED_TABLES
    stale = ALL_CLASSIFIED_TABLES - actual
    if missing or stale:
        raise RuntimeError(
            "RLS classification does not match ORM metadata: "
            f"unclassified={sorted(missing)}, stale={sorted(stale)}"
        )

    for table in TENANT_AND_ORGANIZATION_TABLES:
        columns = frozenset(columns_by_table[table])
        if not {"tenant_id", "organization_id"} <= columns:
            raise RuntimeError(f"{table} requires tenant_id and organization_id for RLS")
    for table in TENANT_ONLY_TABLES | NULLABLE_TENANT_AUDIT_TABLES:
        if "tenant_id" not in columns_by_table[table]:
            raise RuntimeError(f"{table} requires tenant_id for RLS")


def enable_baseline_rls(operations: Any, bind: Any) -> None:
    for table in sorted(TENANT_AND_ORGANIZATION_TABLES):
        enable_tenant_organization_rls(operations, bind, table)
    for table in sorted(TENANT_ONLY_TABLES):
        enable_tenant_only_rls(operations, bind, table)
    for table in sorted(NULLABLE_TENANT_AUDIT_TABLES):
        enable_nullable_tenant_audit_rls(operations, bind, table)


def disable_baseline_rls(operations: Any, bind: Any) -> None:
    for table in sorted(NULLABLE_TENANT_AUDIT_TABLES, reverse=True):
        disable_nullable_tenant_audit_rls(operations, bind, table)
    for table in sorted(TENANT_ONLY_TABLES, reverse=True):
        disable_tenant_only_rls(operations, bind, table)
    for table in sorted(TENANT_AND_ORGANIZATION_TABLES, reverse=True):
        disable_tenant_organization_rls(operations, bind, table)


__all__ = [
    "ALL_CLASSIFIED_TABLES",
    "INTENTIONAL_RLS_EXCLUSIONS",
    "INTENTIONAL_RLS_EXCLUSION_TABLES",
    "NULLABLE_TENANT_AUDIT_TABLES",
    "TENANT_AND_ORGANIZATION_TABLES",
    "TENANT_ONLY_TABLES",
    "disable_baseline_rls",
    "enable_baseline_rls",
    "validate_rls_classification",
]
