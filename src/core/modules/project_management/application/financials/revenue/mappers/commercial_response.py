from __future__ import annotations

from src.core.modules.project_management.application.financials.revenue.dto.responses.commercial_projection import (
    ProjectCommercialProjection,
)
from src.core.modules.project_management.application.financials.revenue.dto.responses.commercial_response import (
    FinancialCommercialProjectionDto,
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
        approved_preparation_amount=format(projection.approved_preparation_amount, "f"),
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
        as_of_date=projection.as_of_date.isoformat() if projection.as_of_date else "",
        revenue_availability=projection.revenue_availability,
        margin_availability=projection.margin_availability,
        percent_availability=projection.percent_availability,
        revenue_reason=projection.revenue_reason,
        margin_reason=projection.margin_reason,
        percent_reason=projection.percent_reason,
    )
