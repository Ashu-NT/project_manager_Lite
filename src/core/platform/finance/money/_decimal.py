from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import TypeAlias

from src.core.platform.common.exceptions import ValidationError


DecimalInput: TypeAlias = Decimal | int | str


def decimal_value(value: DecimalInput, *, label: str = "Decimal value") -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValidationError(
            f"{label} must use Decimal, integer, or canonical decimal text; binary floats are forbidden.",
            code="DECIMAL_BINARY_FLOAT_FORBIDDEN",
        )
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{label} is required.", code="DECIMAL_VALUE_REQUIRED")
    try:
        resolved = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(
            f"{label} must be a valid decimal value.",
            code="DECIMAL_VALUE_INVALID",
        ) from exc
    if not resolved.is_finite():
        raise ValidationError(
            f"{label} must be finite.",
            code="DECIMAL_VALUE_NON_FINITE",
        )
    return Decimal("0") if resolved.is_zero() else resolved


def decimal_from_legacy_float(value: float, *, label: str = "Legacy decimal value") -> Decimal:
    # TRANSITION(PF-A1-LEGACY-FLOAT): Migration and legacy-adapter input only.
    # Remove after Phase D float-column and float-DTO retirement.
    if isinstance(value, bool) or not isinstance(value, float) or not math.isfinite(value):
        raise ValidationError(
            f"{label} must be a finite binary float.",
            code="LEGACY_FLOAT_INVALID",
        )
    return decimal_value(str(value), label=label)


def canonical_decimal_text(value: DecimalInput) -> str:
    resolved = decimal_value(value)
    if resolved.is_zero():
        return "0"
    return format(resolved.normalize(), "f")


__all__ = [
    "DecimalInput",
    "canonical_decimal_text",
    "decimal_from_legacy_float",
    "decimal_value",
]
