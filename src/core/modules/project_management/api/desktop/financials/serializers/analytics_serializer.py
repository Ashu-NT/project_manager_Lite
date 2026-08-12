"""Analytics row serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialAnalyticsRowDto
from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.platform.finance.money import canonical_decimal_text


def serialize_analytics(rows, currency: str | None) -> tuple[FinancialAnalyticsRowDto, ...]:
    return tuple(
        FinancialAnalyticsRowDto(
            dimension=row.dimension,
            key=row.key,
            label=row.label,
            planned=canonical_decimal_text(row.planned),
            planned_label=format_money(row.planned, currency),
            committed=canonical_decimal_text(row.committed),
            committed_label=format_money(row.committed, currency),
            actual=canonical_decimal_text(row.actual),
            actual_label=format_money(row.actual, currency),
            forecast=canonical_decimal_text(row.forecast),
            forecast_label=format_money(row.forecast, currency),
            exposure=canonical_decimal_text(row.exposure),
            exposure_label=format_money(row.exposure, currency),
        )
        for row in rows
    )


__all__ = ["serialize_analytics"]
