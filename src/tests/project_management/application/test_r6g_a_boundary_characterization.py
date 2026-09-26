from dataclasses import fields
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricAvailability,
)
from src.core.modules.project_management.gateway.billing.accounting_billing import (
    BillingPreparationLinePayload,
    ProjectBillingPreparationPayload,
)
from src.tests.project_management.application.test_project_finance_profitability_projection import (
    _approve_forecast_with_etc,
    _create_billing_profile,
    _setup_billable_project,
)


def test_pm_only_commercial_workflow_needs_no_optional_operational_module(services):
    registry = services["module_registry"]
    assert registry.is_module_enabled("project_management")
    for module in ("accounting", "inventory", "procurement", "inventory_procurement"):
        assert not registry.is_module_enabled(module)

    _, project, cost_code = _setup_billable_project(services, name="PM-only commercial")
    _create_billing_profile(services, project.id, contract_value=Decimal(1000))
    _approve_forecast_with_etc(services, project.id, cost_code, etc_amount="750")
    preparation = services["billing_preparation_service"].create_preparation(
        project.id,
        preparation_number="PM-ONLY",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        idempotency_key="pm-only-preparation",
    )
    projection = services["reporting_service"].get_project_commercial_projection(
        project.id, as_of_date=date(2026, 8, 31)
    )
    assert preparation.project_id == project.id
    assert projection.revenue_availability is CommercialMetricAvailability.AVAILABLE
    assert projection.forecast_revenue_at_completion == Decimal(1000)
    assert projection.projected_margin_amount == Decimal(250)
    assert projection.projected_margin_percent == Decimal(25)


def test_pm_billing_payload_describes_evidence_not_accounting_decisions():
    header = {field.name for field in fields(ProjectBillingPreparationPayload)}
    line = {field.name for field in fields(BillingPreparationLinePayload)}
    assert {
        "tenant_id",
        "organization_id",
        "project_id",
        "preparation_id",
        "approved_by",
        "approved_at",
    } <= header
    assert {
        "source_type",
        "source_id",
        "source_revision",
        "source_content_hash",
    } <= line
    assert not (
        {
            "invoice_number",
            "tax_amount",
            "gl_account",
            "ar_account",
            "paid_amount",
            "statutory_posting_date",
        }
        & (header | line)
    )
