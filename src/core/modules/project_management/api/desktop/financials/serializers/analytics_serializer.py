"""Analytics row serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialAnalyticsRowDto
from src.core.modules.project_management.api.desktop.financials.formatters.money_formatter import format_money


def serialize_analytics(rows, currency: str | None) -> tuple[FinancialAnalyticsRowDto, ...]:
    return tuple(
        FinancialAnalyticsRowDto(
            dimension=row.dimension,
            key=row.key,
            label=row.label,
            planned=float(row.planned or 0.0),
            planned_label=format_money(row.planned, currency),
            committed=float(row.committed or 0.0),
            committed_label=format_money(row.committed, currency),
            actual=float(row.actual or 0.0),
            actual_label=format_money(row.actual, currency),
            forecast=float(row.forecast or 0.0),
            forecast_label=format_money(row.forecast, currency),
            exposure=float(row.exposure or 0.0),
            exposure_label=format_money(row.exposure, currency),
        )
        for row in rows
    )


__all__ = ["serialize_analytics"]
