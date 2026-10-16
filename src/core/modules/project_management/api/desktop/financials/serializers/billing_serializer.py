from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.billing import (
    FinancialBillingPreparationDto,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationResponse,
)


def serialize_billing_preparation(
    preparation: FinancialBillingPreparationResponse,
) -> FinancialBillingPreparationDto:
    return FinancialBillingPreparationDto(
        id=preparation.id,
        preparation_number=preparation.preparation_number,
        billing_method=preparation.billing_method,
        status=preparation.status,
        period_label=f"{preparation.period_start.isoformat()} - {preparation.period_end.isoformat()}",
        line_count=preparation.line_count,
        total_amount=preparation.total_amount,
        currency_code=preparation.currency_code,
        row_version=preparation.row_version,
    )


__all__ = ["serialize_billing_preparation"]
