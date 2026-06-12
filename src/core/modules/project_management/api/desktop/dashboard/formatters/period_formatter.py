"""Period and time-window formatting helpers."""

from __future__ import annotations
from datetime import date, datetime, timedelta, timezone


def fmt_period_axis_label(
    period_end: date,
    *,
    selected_period_key: str,
    series_length: int,
) -> str:
    normalized_key = (selected_period_key or "").strip().lower()
    if normalized_key in {"30d", "60d", "90d"}:
        return period_end.strftime("%d %b")
    if normalized_key == "180d":
        return period_end.strftime("%b %Y" if series_length > 6 else "%d %b")
    return period_end.strftime("%b %Y")


def period_cutoff_date(selected_period_key: str) -> date | None:
    days_by_key = {"30d": 30, "60d": 60, "90d": 90, "180d": 180}
    days = days_by_key.get((selected_period_key or "").strip().lower())
    if days is None:
        return None
    return date.today() - timedelta(days=days)


def period_cutoff_datetime(selected_period_key: str) -> datetime | None:
    cutoff = period_cutoff_date(selected_period_key)
    if cutoff is None:
        return None
    return datetime.combine(cutoff, datetime.min.time(), tzinfo=timezone.utc)


__all__ = ["fmt_period_axis_label", "period_cutoff_date", "period_cutoff_datetime"]
