from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.billing import (
    FinancialBillingPreparationDto,
    FinancialBillingPreparationLineDto,
    FinancialBillingProfileDto,
    FinancialBillingScheduleLineDto,
    FinancialCommercialProjectionDto,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingExternalEvent,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)


def serialize_billing_profile(
    profile: ProjectBillingProfile | None,
) -> FinancialBillingProfileDto:
    if profile is None:
        return FinancialBillingProfileDto()
    return FinancialBillingProfileDto(
        id=profile.id,
        status=profile.status.value,
        currency_code=profile.currency_code,
        contract_reference=profile.contract_reference,
        contract_value=format(profile.contract_value, "f"),
        customer_party_id=profile.customer_party_id or "",
        external_customer_reference=profile.external_customer_reference or "",
        purchase_order_reference=profile.purchase_order_reference or "",
        payment_terms_days=profile.payment_terms_days,
        row_version=profile.row_version,
    )


def serialize_billing_schedule_line(
    line: ProjectBillingScheduleLine,
) -> FinancialBillingScheduleLineDto:
    return FinancialBillingScheduleLineDto(
        id=line.id,
        name=line.name,
        status=line.status.value,
        amount=format(line.amount, "f"),
        currency_code=line.currency_code,
        due_date=line.due_date.isoformat(),
        task_id=line.task_id or "",
        acceptance_reference=line.acceptance_reference or "",
        row_version=line.row_version,
    )


def serialize_billing_preparation(
    preparation: ProjectBillingPreparation,
    *,
    latest_external_event: ProjectBillingExternalEvent | None = None,
) -> FinancialBillingPreparationDto:
    return FinancialBillingPreparationDto(
        id=preparation.id,
        preparation_number=preparation.preparation_number,
        billing_method=preparation.billing_method.value,
        status=preparation.status.value,
        period_label=f"{preparation.period_start.isoformat()} - {preparation.period_end.isoformat()}",
        line_count=preparation.line_count,
        total_amount=format(preparation.total_amount, "f"),
        currency_code=preparation.currency_code,
        external_system=(latest_external_event.external_system if latest_external_event else ""),
        external_status=(latest_external_event.external_status if latest_external_event else ""),
        external_invoice_reference=(
            (latest_external_event.external_invoice_reference or "") if latest_external_event else ""
        ),
        reconciliation_reference=(
            (latest_external_event.reconciliation_reference or "") if latest_external_event else ""
        ),
        row_version=preparation.row_version,
    )


def serialize_billing_preparation_line(
    line: ProjectBillingPreparationLine,
) -> FinancialBillingPreparationLineDto:
    return FinancialBillingPreparationLineDto(
        id=line.id,
        preparation_id=line.preparation_id,
        source_type=line.source_type.value,
        source_id=line.source_id,
        description=line.description,
        source_date=line.source_date.isoformat(),
        quantity=format(line.quantity, "f"),
        unit=line.unit,
        unit_rate=format(line.unit_rate, "f"),
        net_amount=format(line.net_amount, "f"),
        currency_code=line.currency_code,
        task_id=line.task_id or "",
        resource_id=line.resource_id or "",
    )


def serialize_commercial_projection(
    projection: ProjectCommercialProjection,
) -> FinancialCommercialProjectionDto:
    return FinancialCommercialProjectionDto(
        project_id=projection.project_id,
        project_currency=projection.project_currency or "",
        contract_value=(
            format(projection.contract_value, "f")
            if projection.contract_value is not None
            else ""
        ),
        billable_amount=format(projection.billable_amount, "f"),
        externally_invoiced_amount=format(projection.externally_invoiced_amount, "f"),
        externally_paid_amount=format(projection.externally_paid_amount, "f"),
        external_accounting_data_available=projection.external_accounting_data_available,
        forecast_revenue_at_completion=(
            format(projection.forecast_revenue_at_completion, "f")
            if projection.forecast_revenue_at_completion is not None
            else ""
        ),
        revenue_basis=projection.revenue_basis,
        projected_margin_amount=(
            format(projection.projected_margin_amount, "f")
            if projection.projected_margin_amount is not None
            else ""
        ),
        projected_margin_percent=(
            format(projection.projected_margin_percent, "f")
            if projection.projected_margin_percent is not None
            else ""
        ),
        profitability_detail_included=projection.profitability_detail_included,
    )


__all__ = [
    "serialize_billing_preparation",
    "serialize_billing_preparation_line",
    "serialize_billing_profile",
    "serialize_billing_schedule_line",
    "serialize_commercial_projection",
]
