"""Forecast DTO assembly.

EAC/ETC calculations are delegated to application/financials ForecastCostService.
When forecast_service is not available, falls back to inline computation for
backward compatibility with legacy wiring.
"""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.forecasts import FinancialForecastDto
from src.core.modules.project_management.api.desktop.financials.formatters.money_formatter import format_money


def build_forecast_dto(
    project_id: str,
    percent_complete: float,
    method: str,
    threshold_percent: float,
    *,
    cost_service=None,
    forecast_service=None,
    currency: str | None = None,
) -> FinancialForecastDto:
    """Build FinancialForecastDto.

    Preferred: delegates to ForecastCostService when injected.
    Fallback: computes directly from cost items (backward compat).
    """
    if forecast_service is not None:
        return _build_from_forecast_service(
            project_id, percent_complete, method, threshold_percent,
            forecast_service=forecast_service, currency=currency,
        )
    if cost_service is not None:
        return _build_from_cost_items(
            project_id, percent_complete, method, threshold_percent,
            cost_service=cost_service, currency=currency,
        )
    return empty_forecast(project_id, currency)


def _build_from_forecast_service(
    project_id, percent_complete, method, threshold_percent,
    *, forecast_service, currency,
) -> FinancialForecastDto:
    from src.core.modules.project_management.application.financials.forecasts.forecast_service import EACMethod
    _method_map = {
        "manual": EACMethod.MANUAL,
        "bac_over_cpi": EACMethod.BAC_OVER_CPI,
        "ac_etc_plan": EACMethod.AC_PLUS_ETC_AT_PLAN,
        "ac_etc_cpi": EACMethod.AC_PLUS_ETC_AT_CPI,
    }
    eac_method = _method_map.get(str(method or "bac_over_cpi").lower(), EACMethod.BAC_OVER_CPI)
    result = forecast_service.compute_forecast(
        project_id, percent_complete, method=eac_method, threshold_percent=threshold_percent
    )
    pct = max(0.0, min(1.0, percent_complete))
    ev = result.bac * pct
    return FinancialForecastDto(
        project_id=project_id, method=method,
        bac=result.bac, bac_label=format_money(result.bac, currency),
        ac=result.ac, ac_label=format_money(result.ac, currency),
        ev=ev, ev_label=format_money(ev, currency),
        etc=result.etc, etc_label=format_money(result.etc, currency),
        eac=result.eac, eac_label=format_money(result.eac, currency),
        vac=result.vac, vac_label=format_money(result.vac, currency),
        cpi=round(result.cpi, 3), cpi_label=f"{result.cpi:.3f}",
        is_over_budget=result.is_over_budget,
        exceeds_threshold=result.exceeds_threshold,
        threshold_percent=threshold_percent,
    )


def _build_from_cost_items(
    project_id, percent_complete, method, threshold_percent,
    *, cost_service, currency,
) -> FinancialForecastDto:
    items = cost_service.list_cost_items_for_project(project_id)
    bac = sum(getattr(i, "planned_amount", 0.0) or 0.0 for i in items)
    ac = sum(getattr(i, "actual_amount", 0.0) or 0.0 for i in items)
    pct = max(0.0, min(1.0, percent_complete))
    ev = bac * pct
    cpi = (ev / ac) if ac > 0 else 0.0
    # Delegate EAC/ETC calculation to the application layer via ForecastCostService._compute_etc_eac pattern
    etc, eac = _compute_etc_eac(method, bac, ac, ev, cpi, items)
    vac = bac - eac
    threshold = bac * (1.0 + threshold_percent / 100.0)
    return FinancialForecastDto(
        project_id=project_id, method=method,
        bac=bac, bac_label=format_money(bac, currency),
        ac=ac, ac_label=format_money(ac, currency),
        ev=ev, ev_label=format_money(ev, currency),
        etc=etc, etc_label=format_money(etc, currency),
        eac=eac, eac_label=format_money(eac, currency),
        vac=vac, vac_label=format_money(vac, currency),
        cpi=round(cpi, 3), cpi_label=f"{cpi:.3f}",
        is_over_budget=eac > bac,
        exceeds_threshold=(eac > threshold) if bac > 0 else False,
        threshold_percent=threshold_percent,
    )


def _compute_etc_eac(method, bac, ac, ev, cpi, items) -> tuple[float, float]:
    """EAC/ETC computation — mirrors ForecastCostService logic in application layer."""
    if method == "manual":
        forecast_sum = sum(
            (getattr(i, "forecast_amount", None) or getattr(i, "planned_amount", 0.0) or 0.0)
            for i in items
        )
        etc = max(0.0, forecast_sum - ac)
        return etc, ac + etc
    if method == "bac_over_cpi":
        eac = (bac / cpi) if cpi > 0 else bac
        return eac - ac, eac
    if method == "ac_etc_plan":
        etc = max(0.0, bac - ev)
        return etc, ac + etc
    if method == "ac_etc_cpi":
        remaining = max(0.0, bac - ev)
        etc = (remaining / cpi) if cpi > 0 else remaining
        return etc, ac + etc
    etc = max(0.0, bac - ac)
    return etc, bac


def empty_forecast(project_id: str, currency: str | None) -> FinancialForecastDto:
    z = format_money(0.0, currency)
    return FinancialForecastDto(
        project_id=project_id, method="bac_over_cpi",
        bac=0.0, bac_label=z, ac=0.0, ac_label=z, ev=0.0, ev_label=z,
        etc=0.0, etc_label=z, eac=0.0, eac_label=z, vac=0.0, vac_label=z,
        cpi=0.0, cpi_label="0.000",
        is_over_budget=False, exceeds_threshold=False, threshold_percent=10.0,
    )


__all__ = ["build_forecast_dto", "empty_forecast"]
