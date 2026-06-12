from __future__ import annotations

from datetime import date


def format_amount(value: float) -> str:
    return f"{value:.2f}"


def format_date_iso(d: date | None) -> str:
    return d.isoformat() if d else ""
