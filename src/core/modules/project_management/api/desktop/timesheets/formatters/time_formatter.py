from __future__ import annotations

from decimal import Decimal


def format_hours(value: Decimal | float | None) -> str:
    return f"{float(value or 0.0):.2f}h"


__all__ = ["format_hours"]
