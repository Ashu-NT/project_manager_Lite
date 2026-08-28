from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_period,
    period_bounds,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceLedgerRow,
    FinancePeriodRow,
)


def build_period_cost_phasing(
    *,
    ledger: list[FinanceLedgerRow],
    period: str,
    as_of: date,
) -> list[FinancePeriodRow]:
    if not ledger:
        return []

    normalized_period = normalize_period(period)
    buckets: dict[str, dict[str, object]] = {}
    for entry in ledger:
        anchor = entry.occurred_on or as_of
        period_key, start, end = period_bounds(anchor, normalized_period)
        bucket = buckets.get(period_key)
        if bucket is None:
            bucket = {
                "period_key": period_key,
                "period_start": start,
                "period_end": end,
                "planned": Decimal("0"),
                "committed": Decimal("0"),
                "actual": Decimal("0"),
                "forecast": Decimal("0"),
            }
            buckets[period_key] = bucket
        if entry.stage in {"planned", "committed", "actual", "forecast"}:
            bucket[entry.stage] = Decimal(bucket[entry.stage] or 0) + entry.amount

    out: list[FinancePeriodRow] = []
    for row in sorted(buckets.values(), key=lambda item: item["period_start"]):
        planned = Decimal(row["planned"] or 0)
        committed = Decimal(row["committed"] or 0)
        actual = Decimal(row["actual"] or 0)
        forecast = Decimal(row["forecast"] or 0)
        out.append(
            FinancePeriodRow(
                period_key=str(row["period_key"]),
                period_start=row["period_start"],  # type: ignore[arg-type]
                period_end=row["period_end"],  # type: ignore[arg-type]
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=forecast,
                exposure=actual + forecast,
            )
        )
    return out


__all__ = ["build_period_cost_phasing"]
