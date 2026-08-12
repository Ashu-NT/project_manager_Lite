from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsForecastMetricViewModel,
    FinancialsForecastViewModel,
)


def build_forecast_view_model(forecast_dto: Any) -> FinancialsForecastViewModel:
    alert = ""
    if not forecast_dto.has_approved_forecast:
        alert = "No approved forecast exists for this as-of date. EAC and VAC are unavailable."
    elif forecast_dto.is_over_budget:
        alert = "Approved forecast EAC exceeds the approved budget. Review the forecast variance."

    metrics = (
        FinancialsForecastMetricViewModel(
            label="Approved budget", value=forecast_dto.budget_label
        ),
        FinancialsForecastMetricViewModel(
            label="Posted actual", value=forecast_dto.actual_label
        ),
        FinancialsForecastMetricViewModel(label="ETC", value=forecast_dto.etc_label),
        FinancialsForecastMetricViewModel(
            label="EAC",
            value=forecast_dto.eac_label,
            color_hint="danger" if forecast_dto.is_over_budget else "success",
        ),
        FinancialsForecastMetricViewModel(
            label="VAC",
            value=forecast_dto.vac_label,
            color_hint=(
                ""
                if forecast_dto.vac is None
                else "danger" if forecast_dto.is_over_budget else "success"
            ),
        ),
    )
    return FinancialsForecastViewModel(
        basis_label=forecast_dto.basis_label,
        budget_label=forecast_dto.budget_label,
        actual_label=forecast_dto.actual_label,
        etc_label=forecast_dto.etc_label,
        eac_label=forecast_dto.eac_label,
        vac_label=forecast_dto.vac_label,
        is_over_budget=forecast_dto.is_over_budget,
        has_approved_forecast=forecast_dto.has_approved_forecast,
        forecast_revision=forecast_dto.forecast_revision,
        forecast_as_of_label=(
            "" if forecast_dto.forecast_as_of is None
            else forecast_dto.forecast_as_of.isoformat()
        ),
        alert_message=alert,
        metrics=metrics,
    )


__all__ = ["build_forecast_view_model"]
