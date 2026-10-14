from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceAnalyticsRow,
)


def build_source_analytics(source_rows: list[Any]) -> list[FinanceAnalyticsRow]:
    rows: list[FinanceAnalyticsRow] = []
    for src in source_rows:
        planned = Decimal(getattr(src, "planned", 0) or 0)
        committed = Decimal(getattr(src, "committed", 0) or 0)
        actual = Decimal(getattr(src, "actual", 0) or 0)
        forecast = Decimal(getattr(src, "forecast", 0) or 0)
        rows.append(
            FinanceAnalyticsRow(
                dimension="source",
                key=str(getattr(src, "source_key", "")),
                label=str(getattr(src, "source_label", "")),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=forecast,
                exposure=actual + committed,
            )
        )
    rows.sort(key=lambda row: (-(row.exposure), row.label.lower()))
    return rows


__all__ = ["build_source_analytics"]
