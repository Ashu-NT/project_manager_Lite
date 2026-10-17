"""Display-only formatting for the Review Queue."""

from datetime import date, datetime
from decimal import Decimal


def format_hours(value: Decimal | float | None) -> str:
    return "-" if value is None else f"{value:.2f}h"


def format_period_label(period_start: date) -> str:
    return period_start.strftime("%b %Y")


def format_datetime(value: datetime | None) -> str:
    return "-" if value is None else value.strftime("%Y-%m-%d %H:%M")
