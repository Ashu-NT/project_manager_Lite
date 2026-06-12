"""Number, percentage, and ratio formatting helpers."""

from __future__ import annotations
from typing import Any


def fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_float(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return f"{0.0:,.{decimals}f}"


def fmt_percent(value: Any, decimals: int = 2) -> str:
    return f"{fmt_float(value, decimals)}%"


def fmt_ratio(value: Any) -> str:
    if value is None:
        return "-"
    return fmt_float(value, 2)


__all__ = ["fmt_float", "fmt_int", "fmt_percent", "fmt_ratio"]
