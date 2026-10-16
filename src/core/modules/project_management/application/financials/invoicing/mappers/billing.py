from __future__ import annotations

from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationLineDto,
    FinancialBillingPreparationResponse,
    FinancialBillingProfileDto,
    FinancialBillingScheduleLineDto,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
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


def map_billing_preparation(preparation: ProjectBillingPreparation) -> FinancialBillingPreparationResponse:
    return FinancialBillingPreparationResponse(
        id=preparation.id,
        project_id=preparation.project_id,
        preparation_number=preparation.preparation_number,
        billing_method=preparation.billing_method.value,
        status=preparation.status.value,
        period_start=preparation.period_start,
        period_end=preparation.period_end,
        line_count=preparation.line_count,
        total_amount=format(preparation.total_amount, "f"),
        currency_code=preparation.currency_code,
        row_version=preparation.row_version,
    )
