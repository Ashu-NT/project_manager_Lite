"""Map canonical application forecast results to desktop DTOs."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.forecasts import (
    FinancialForecastDto,
)
from src.core.modules.project_management.application.financials import (
    EACMethod,
    ForecastCostService,
)


def build_forecast_dto(
    project_id: str,
    percent_complete: float,
    method: str,
    threshold_percent: float,
    *,
    forecast_service: ForecastCostService,
    currency: str | None = None,
) -> FinancialForecastDto:
    method_map = {
        "manual": EACMethod.MANUAL,
        "bac_over_cpi": EACMethod.BAC_OVER_CPI,
        "ac_etc_plan": EACMethod.AC_PLUS_ETC_AT_PLAN,
        "ac_etc_cpi": EACMethod.AC_PLUS_ETC_AT_CPI,
    }
    eac_method = method_map.get(
        str(method or EACMethod.BAC_OVER_CPI.value).strip().lower(),
        EACMethod.BAC_OVER_CPI,
    )
    result = forecast_service.compute_forecast(
        project_id,
        percent_complete,
        method=eac_method,
        threshold_percent=threshold_percent,
    )
    return FinancialForecastDto(
        project_id=project_id,
        method=result.method.value,
        bac=result.bac,
        bac_label=format_money(result.bac, currency),
        ac=result.ac,
        ac_label=format_money(result.ac, currency),
        ev=result.ev,
        ev_label=format_money(result.ev, currency),
        etc=result.etc,
        etc_label=format_money(result.etc, currency),
        eac=result.eac,
        eac_label=format_money(result.eac, currency),
        vac=result.vac,
        vac_label=format_money(result.vac, currency),
        cpi=round(result.cpi, 3),
        cpi_label=f"{result.cpi:.3f}",
        is_over_budget=result.is_over_budget,
        exceeds_threshold=result.exceeds_threshold,
        threshold_percent=result.threshold_percent,
    )


__all__ = ["build_forecast_dto"]
