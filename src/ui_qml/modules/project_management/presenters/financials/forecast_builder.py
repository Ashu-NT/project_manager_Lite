from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsForecastMetricViewModel,
    FinancialsForecastViewModel,
)

_METHOD_LABELS = {
    "bac_over_cpi": "BAC / CPI",
    "ac_etc_plan": "AC + ETC at plan rate",
    "ac_etc_cpi": "AC + ETC at CPI rate",
    "manual": "Manual (sum of forecast amounts)",
}


def build_forecast_view_model(forecast_dto) -> FinancialsForecastViewModel:
    method_label = _METHOD_LABELS.get(forecast_dto.method, forecast_dto.method)
    alert = ""
    if forecast_dto.exceeds_threshold:
        pct = forecast_dto.threshold_percent
        alert = (
            f"EAC exceeds planned budget by more than {pct:.0f}%. "
            "Cost approval may be required."
        )
    elif forecast_dto.is_over_budget:
        alert = "EAC exceeds the planned budget (BAC). Review cost exposure."
    cpi_hint = ""
    if forecast_dto.cpi > 0:
        cpi_hint = (
            "success" if forecast_dto.cpi >= 1.0 else "warning" if forecast_dto.cpi >= 0.9 else "danger"
        )
    metrics = (
        FinancialsForecastMetricViewModel(label="BAC", value=forecast_dto.bac_label),
        FinancialsForecastMetricViewModel(label="AC", value=forecast_dto.ac_label),
        FinancialsForecastMetricViewModel(label="EV", value=forecast_dto.ev_label),
        FinancialsForecastMetricViewModel(label="ETC", value=forecast_dto.etc_label),
        FinancialsForecastMetricViewModel(
            label="EAC",
            value=forecast_dto.eac_label,
            color_hint="danger" if forecast_dto.is_over_budget else "success",
        ),
        FinancialsForecastMetricViewModel(
            label="VAC",
            value=forecast_dto.vac_label,
            color_hint="danger" if forecast_dto.vac < 0 else "success",
        ),
        FinancialsForecastMetricViewModel(
            label="CPI",
            value=forecast_dto.cpi_label,
            color_hint=cpi_hint,
        ),
    )
    return FinancialsForecastViewModel(
        method=forecast_dto.method,
        method_label=method_label,
        bac_label=forecast_dto.bac_label,
        ac_label=forecast_dto.ac_label,
        ev_label=forecast_dto.ev_label,
        etc_label=forecast_dto.etc_label,
        eac_label=forecast_dto.eac_label,
        vac_label=forecast_dto.vac_label,
        cpi_label=forecast_dto.cpi_label,
        is_over_budget=forecast_dto.is_over_budget,
        exceeds_threshold=forecast_dto.exceeds_threshold,
        threshold_percent=forecast_dto.threshold_percent,
        alert_message=alert,
        metrics=metrics,
    )
