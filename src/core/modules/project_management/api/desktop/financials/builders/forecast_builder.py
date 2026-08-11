"""Map the canonical approved-forecast control snapshot to desktop DTOs."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.forecasts import (
    FinancialForecastDto,
)
def build_forecast_dto(
    project_id: str,
    *,
    snapshot,
    currency: str | None = None,
) -> FinancialForecastDto:
    has_forecast = snapshot.forecast_etc is not None
    eac = snapshot.estimate_at_completion
    vac = snapshot.variance_at_completion
    return FinancialForecastDto(
        project_id=project_id,
        basis="approved_forecast",
        basis_label="Approved forecast" if has_forecast else "No approved forecast",
        budget=float(snapshot.budget),
        budget_label=format_money(snapshot.budget, currency),
        actual=float(snapshot.actual),
        actual_label=format_money(snapshot.actual, currency),
        etc=None if not has_forecast else float(snapshot.forecast_etc),
        etc_label=(
            format_money(snapshot.forecast_etc, currency)
            if has_forecast else "Not approved"
        ),
        eac=None if eac is None else float(eac),
        eac_label="Not available" if eac is None else format_money(eac, currency),
        vac=None if vac is None else float(vac),
        vac_label="Not available" if vac is None else format_money(vac, currency),
        is_over_budget=bool(vac is not None and vac < 0),
        has_approved_forecast=has_forecast,
        forecast_revision=snapshot.approved_forecast_revision,
        forecast_as_of=snapshot.approved_forecast_as_of,
    )


__all__ = ["build_forecast_dto"]
