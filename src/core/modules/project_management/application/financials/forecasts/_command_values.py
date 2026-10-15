from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from src.core.platform.common.exceptions import ValidationError


def command_amount(value: str) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            "Forecast amount must be a canonical decimal value.",
            code="PROJECT_FORECAST_AMOUNT_INVALID",
        ) from exc
    if not amount.is_finite():
        raise ValidationError(
            "Forecast amount must be finite.",
            code="PROJECT_FORECAST_AMOUNT_INVALID",
        )
    return amount


def command_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise ValidationError(
            f"{label} must use YYYY-MM-DD.",
            code="PROJECT_FORECAST_DATE_INVALID",
        ) from exc


def optional_command_date(value: str) -> date | None:
    return command_date(value, "Forecast period date") if value else None


def _validate_period(start: date | None, end: date | None) -> None:
    if (start is None) != (end is None):
        raise ValidationError(
            "Forecast period start and end must be provided together.",
            code="PROJECT_FORECAST_GENERATION_PERIOD_INCOMPLETE",
        )
    if start and end and end < start:
        raise ValidationError(
            "Forecast period end cannot precede period start.",
            code="PROJECT_FORECAST_GENERATION_PERIOD_INVALID",
        )
