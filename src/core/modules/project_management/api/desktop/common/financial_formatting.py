from __future__ import annotations

from decimal import Decimal
from typing import TypeAlias

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.finance.money._decimal import (
    decimal_from_legacy_float,
    decimal_value,
)
from src.core.platform.finance.money.currency import CurrencyCode
from src.core.platform.finance.money.rounding import DEFAULT_ROUNDING_POLICY


DesktopNumericInput: TypeAlias = Decimal | int | str | float


def _desktop_decimal(value: DesktopNumericInput, *, label: str) -> Decimal:
    if isinstance(value, float):
        # TRANSITION(PF-A1-DESKTOP-FLOAT): Existing PM read DTOs still expose floats.
        # Delete this branch when Phase D switches all financial DTOs to decimal text.
        return decimal_from_legacy_float(value, label=label)
    return decimal_value(value, label=label)


def format_decimal_amount(
    value: DesktopNumericInput | None,
    *,
    places: int = 2,
    grouping: bool = True,
    signed: bool = False,
    fallback: str | None = None,
) -> str:
    if value is None:
        if fallback is not None:
            return fallback
        amount = Decimal("0")
    else:
        amount = _desktop_decimal(value, label="Desktop financial amount")
    rounded = DEFAULT_ROUNDING_POLICY.quantize(amount, scale=places)
    grouping_token = "," if grouping else ""
    sign_token = "+" if signed else ""
    return format(rounded, f"{sign_token}{grouping_token}.{places}f")


def format_money(
    value: DesktopNumericInput | None,
    currency: str | None = None,
    *,
    fallback: str | None = None,
) -> str:
    if value is None and fallback is not None:
        return fallback
    resolved_currency = str(currency or "").strip()
    if not resolved_currency:
        return format_decimal_amount(value)
    currency_code = CurrencyCode(resolved_currency)
    places = currency_code.minor_units
    if places is None:
        raise ValidationError(
            f"Currency code '{currency_code.code}' has no ISO 4217 minor-unit definition.",
            code="CURRENCY_MINOR_UNITS_UNDEFINED",
        )
    return f"{currency_code.code} {format_decimal_amount(value, places=places)}"


def format_signed_money(value: DesktopNumericInput | None) -> str:
    return format_decimal_amount(value, signed=True)


def format_budget(value: DesktopNumericInput | None, currency: str | None) -> str:
    if value is None:
        return "Not set"
    return format_money(value, currency)


def format_hourly_rate(value: DesktopNumericInput | None, currency: str | None) -> str:
    if value is None:
        return "Rate not set"
    amount = format_decimal_amount(value)
    resolved_currency = str(currency or "").strip()
    if not resolved_currency:
        return f"{amount}/hr"
    currency_code = CurrencyCode(resolved_currency)
    currency_code.minor_unit_quantum()
    return f"{amount} {currency_code.code}/hr"


def format_hours(value: DesktopNumericInput | None) -> str:
    return f"{format_decimal_amount(value, places=1)} h"


__all__ = [
    "DesktopNumericInput",
    "format_budget",
    "format_decimal_amount",
    "format_hourly_rate",
    "format_hours",
    "format_money",
    "format_signed_money",
]
