"""Capacity pool assembly."""

from __future__ import annotations
from datetime import date, timedelta

from src.core.modules.project_management.api.desktop.portfolio.models.capacity import PortfolioCapacityResourceDto


def build_capacity_pool(pool_service=None) -> tuple[PortfolioCapacityResourceDto, ...]:
    if pool_service is None:
        return ()
    today = date.today()
    to_date = today + timedelta(days=90)
    try:
        report = pool_service.get_pool_report(from_date=today, to_date=to_date)
    except Exception:
        return ()
    sorted_pool = sorted(report.pool, key=lambda r: float(r.peak_load_percent or 0.0), reverse=True)
    return tuple(
        PortfolioCapacityResourceDto(
            resource_id=str(summary.resource_id or ""),
            resource_name=str(summary.resource_name or summary.resource_id or "Resource"),
            peak_load_percent=float(summary.peak_load_percent or 0.0),
            average_load_percent=float(summary.average_load_percent or 0.0),
            overloaded=bool(summary.overloaded),
            demand_entries=tuple(
                str(d.project_name or d.project_id or "")
                for d in summary.demands
                if d.project_name or d.project_id
            ),
        )
        for summary in sorted_pool
    )


__all__ = ["build_capacity_pool"]
