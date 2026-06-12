"""Budget, rate, hours and display formatting helpers."""

from __future__ import annotations


def format_budget(value: float | None, currency: str | None) -> str:
    if value is None:
        return "Not set"
    amount = f"{float(value):,.2f}"
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount}"
    return amount


def format_hourly_rate(value: float | None, currency: str | None) -> str:
    if value is None:
        return "Rate not set"
    amount = f"{float(value):,.2f}"
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{amount} {resolved_currency}/hr"
    return f"{amount}/hr"


def format_hours(value: float | None) -> str:
    if value is None:
        return "0.0 h"
    return f"{float(value):,.1f} h"


__all__ = ["format_budget", "format_hourly_rate", "format_hours"]
