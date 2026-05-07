from __future__ import annotations

from datetime import date, datetime
from typing import Any


def format_enum_label(value: str | None) -> str:
    normalized = str(value or "").strip().replace("_", " ")
    return normalized.title() if normalized else "-"


def format_date(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.isoformat()


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def format_quantity(value: Any, *, decimals: int = 3) -> str:
    try:
        return f"{float(value or 0.0):,.{decimals}f}"
    except (TypeError, ValueError):
        return f"{0.0:,.{decimals}f}"


def format_amount(value: Any, *, currency: str | None = None) -> str:
    try:
        amount = f"{float(value or 0.0):,.2f}"
    except (TypeError, ValueError):
        amount = f"{0.0:,.2f}"
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount}"
    return amount


def format_bool_label(value: bool) -> str:
    return "Active" if bool(value) else "Inactive"


def clean_text(value: Any, *, default: str = "") -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return default

