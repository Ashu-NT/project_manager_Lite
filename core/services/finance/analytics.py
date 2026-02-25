from __future__ import annotations

from typing import Any

from core.services.finance.models import FinanceAnalyticsRow, FinanceLedgerRow


def build_source_analytics(source_rows: list[Any]) -> list[FinanceAnalyticsRow]:
    rows: list[FinanceAnalyticsRow] = []
    for src in source_rows:
        planned = float(getattr(src, "planned", 0.0) or 0.0)
        committed = float(getattr(src, "committed", 0.0) or 0.0)
        actual = float(getattr(src, "actual", 0.0) or 0.0)
        rows.append(
            FinanceAnalyticsRow(
                dimension="source",
                key=str(getattr(src, "source_key", "")),
                label=str(getattr(src, "source_label", "")),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=float(max(planned, committed)),
                exposure=float(max(committed, actual)),
            )
        )
    rows.sort(key=lambda row: (-(row.exposure), row.label.lower()))
    return rows


def build_dimension_analytics(
    *,
    ledger: list[FinanceLedgerRow],
    dimension: str,
) -> list[FinanceAnalyticsRow]:
    buckets: dict[str, dict[str, float | str]] = {}
    for row in ledger:
        key, label = dimension_key_label(row=row, dimension=dimension)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "key": key,
                "label": label,
                "planned": 0.0,
                "committed": 0.0,
                "actual": 0.0,
            }
            buckets[key] = bucket
        bucket[row.stage] = float(bucket[row.stage] or 0.0) + float(row.amount or 0.0)

    rows: list[FinanceAnalyticsRow] = []
    for bucket in buckets.values():
        planned = float(bucket["planned"] or 0.0)
        committed = float(bucket["committed"] or 0.0)
        actual = float(bucket["actual"] or 0.0)
        rows.append(
            FinanceAnalyticsRow(
                dimension=dimension,
                key=str(bucket["key"]),
                label=str(bucket["label"]),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=float(max(planned, committed)),
                exposure=float(max(committed, actual)),
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
