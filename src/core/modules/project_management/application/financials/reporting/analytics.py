from __future__ import annotations

from typing import Any
from decimal import Decimal

from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceAnalyticsRow,
    FinanceLedgerRow,
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
                exposure=actual + forecast,
            )
        )
    rows.sort(key=lambda row: (-(row.exposure), row.label.lower()))
    return rows


def build_dimension_analytics(
    *,
    ledger: list[FinanceLedgerRow],
    dimension: str,
) -> list[FinanceAnalyticsRow]:
    buckets: dict[str, dict[str, Decimal | str]] = {}
    for row in ledger:
        key, label = dimension_key_label(row=row, dimension=dimension)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "key": key,
                "label": label,
                "planned": Decimal("0"),
                "committed": Decimal("0"),
                "actual": Decimal("0"),
                "forecast": Decimal("0"),
            }
            buckets[key] = bucket
        if row.stage in {"planned", "committed", "actual", "forecast"}:
            bucket[row.stage] = Decimal(bucket[row.stage] or 0) + row.amount

    rows: list[FinanceAnalyticsRow] = []
    for bucket in buckets.values():
        planned = Decimal(bucket["planned"] or 0)
        committed = Decimal(bucket["committed"] or 0)
        actual = Decimal(bucket["actual"] or 0)
        forecast = Decimal(bucket["forecast"] or 0)
        rows.append(
            FinanceAnalyticsRow(
                dimension=dimension,
                key=str(bucket["key"]),
                label=str(bucket["label"]),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=forecast,
                exposure=actual + forecast,
            )
        )
    rows.sort(key=lambda row: (-(row.exposure), row.label.lower()))
    return rows


def dimension_key_label(*, row: FinanceLedgerRow, dimension: str) -> tuple[str, str]:
    if dimension == "cost_type":
        key = row.cost_type or "OTHER"
        return key, key
    if dimension == "resource":
        if row.resource_id:
            return row.resource_id, row.resource_name or row.resource_id
        return "__unassigned__", "Unassigned / Non-labor"
    if dimension == "task":
        if row.task_id:
            return row.task_id, row.task_name or row.task_id
        return "__project_level__", "Project-level / Non-task"
    raise ValueError(f"Unsupported finance analytics dimension: {dimension}")


__all__ = ["build_source_analytics", "build_dimension_analytics"]
