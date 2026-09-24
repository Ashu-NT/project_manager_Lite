from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError

from ._decimal import DecimalInput, decimal_value
from .money import Money


_UNIT_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{0,31}$")


def normalize_unit(value: object) -> str:
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise ValidationError("Quantity unit is required.", code="QUANTITY_UNIT_REQUIRED")
    if not _UNIT_PATTERN.fullmatch(normalized):
        raise ValidationError(
            "Quantity unit must be a normalized 1-32 character unit code.",
            code="QUANTITY_UNIT_INVALID",
        )
    return normalized


@dataclass(frozen=True, slots=True)
class DecimalQuantity:
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", decimal_value(self.value, label="Quantity"))
        object.__setattr__(self, "unit", normalize_unit(self.unit))

    @classmethod
    def of(cls, value: DecimalInput, unit: str) -> DecimalQuantity:
        return cls(value=value, unit=unit)

    def _require_same_unit(self, other: DecimalQuantity) -> None:
        if not isinstance(other, DecimalQuantity) or self.unit != other.unit:
            raise BusinessRuleError(
                f"Cannot combine quantity units '{self.unit}' and '{getattr(other, 'unit', 'unknown')}'.",
                code="QUANTITY_UNIT_MISMATCH",
            )

    def __add__(self, other: DecimalQuantity) -> DecimalQuantity:
        self._require_same_unit(other)
        return DecimalQuantity(self.value + other.value, self.unit)

    def __sub__(self, other: DecimalQuantity) -> DecimalQuantity:
        self._require_same_unit(other)
        return DecimalQuantity(self.value - other.value, self.unit)

    def __mul__(self, scalar: DecimalInput) -> DecimalQuantity:
        return DecimalQuantity(
            self.value * decimal_value(scalar, label="Quantity multiplier"),
            self.unit,
        )


@dataclass(frozen=True, slots=True)
class MonetaryRate:
    money: Money
    per_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.money, Money):
            raise ValidationError(
                "Monetary rate requires a Money value.",
                code="MONETARY_RATE_MONEY_REQUIRED",
            )
        object.__setattr__(self, "per_unit", normalize_unit(self.per_unit))

    def apply(self, quantity: DecimalQuantity) -> Money:
        if not isinstance(quantity, DecimalQuantity) or quantity.unit != self.per_unit:
            raise BusinessRuleError(
                f"Rate unit '{self.per_unit}' does not match quantity unit "
                f"'{getattr(quantity, 'unit', 'unknown')}'.",
                code="MONETARY_RATE_UNIT_MISMATCH",
            )
        return self.money * quantity.value


__all__ = ["DecimalQuantity", "MonetaryRate", "normalize_unit"]
