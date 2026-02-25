from __future__ import annotations

from datetime import date

from core.services.finance.helpers import normalize_period, period_bounds
from core.services.finance.models import FinanceLedgerRow, FinancePeriodRow


def build_period_cashflow(
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
                "planned": 0.0,
                "committed": 0.0,
                "actual": 0.0,
            }
            buckets[period_key] = bucket
        bucket[entry.stage] = float(bucket[entry.stage] or 0.0) + float(entry.amount or 0.0)

    out: list[FinancePeriodRow] = []
    for row in sorted(buckets.values(), key=lambda item: item["period_start"]):
        planned = float(row["planned"] or 0.0)
        committed = float(row["committed"] or 0.0)
        actual = float(row["actual"] or 0.0)
        out.append(
            FinancePeriodRow(
                period_key=str(row["period_key"]),
                period_start=row["period_start"],  # type: ignore[arg-type]
                period_end=row["period_end"],  # type: ignore[arg-type]
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=float(max(planned, committed)),
                exposure=float(max(committed, actual)),
            )
        )
    return out


__all__ = ["build_period_cashflow"]
