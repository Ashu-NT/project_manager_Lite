from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_decimal_amount,
)


def format_amount(value: float) -> str:
    return format_decimal_amount(value, grouping=False)


def format_date_iso(d: date | None) -> str:
    return d.isoformat() if d else ""
