from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta


def normalize_currency(value: str | None, fallback: str | None) -> str:
    code = (value or "").strip().upper()
    if code:
        return code
    fb = (fallback or "").strip().upper()
    return fb or "-"


def resolve_rate(*, pr_rate: float | None, resource_rate: float | None) -> float:
    if pr_rate is not None:
        return float(pr_rate or 0.0)
    return float(resource_rate or 0.0)


def is_effectively_equal(lhs: float, rhs: float) -> bool:
    tolerance = max(0.01, abs(lhs) * 1e-6)
    return abs(lhs - rhs) <= tolerance


def normalize_period(value: str) -> str:
    token = (value or "").strip().lower()
    if token in {"week", "weekly"}:
        return "week"
    return "month"


def period_bounds(anchor: date, period: str) -> tuple[str, date, date]:
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        iso = start.isocalendar()
        return f"{iso.year}-W{iso.week:02d}", start, end

    last_day = monthrange(anchor.year, anchor.month)[1]
    start = date(anchor.year, anchor.month, 1)
    end = date(anchor.year, anchor.month, last_day)
    return f"{anchor.year}-{anchor.month:02d}", start, end


__all__ = [
    "normalize_currency",
    "resolve_rate",
    "is_effectively_equal",
    "normalize_period",
    "period_bounds",
]
