from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

from src.core.platform.common.exceptions import ValidationError

from .money._decimal import DecimalInput, decimal_value


@dataclass(frozen=True, slots=True)
class NumericPrecision:
    name: str
    precision: int
    scale: int

    def __post_init__(self) -> None:
        if self.precision < 1 or self.scale < 0 or self.scale > self.precision:
            raise ValueError("Numeric precision requires 0 <= scale <= precision.")

    @property
    def quantum(self) -> Decimal:
        return Decimal("1").scaleb(-self.scale)

    @property
    def maximum(self) -> Decimal:
        return Decimal(10) ** (self.precision - self.scale) - self.quantum

    def accepts(self, value: DecimalInput) -> bool:
        resolved = decimal_value(value, label=self.name)
        if abs(resolved) > self.maximum:
            return False
        try:
            with localcontext() as context:
                context.prec = max(34, self.precision + self.scale + 2)
                return resolved == resolved.quantize(self.quantum)
        except InvalidOperation:
            return False

    def validate(self, value: DecimalInput) -> Decimal:
        resolved = decimal_value(value, label=self.name)
        if not self.accepts(resolved):
            raise ValidationError(
                f"{self.name} exceeds Numeric({self.precision},{self.scale}) precision or scale.",
                code="FINANCIAL_NUMERIC_OUT_OF_RANGE",
            )
        return resolved


MONEY_STORAGE = NumericPrecision("Money amount", 19, 4)
RATE_STORAGE = NumericPrecision("Monetary rate", 19, 8)
QUANTITY_STORAGE = NumericPrecision("Decimal quantity", 19, 6)
PERCENTAGE_STORAGE = NumericPrecision("Percentage", 9, 6)
EXCHANGE_RATE_STORAGE = NumericPrecision("Exchange rate", 24, 12)


__all__ = [
    "EXCHANGE_RATE_STORAGE",
    "MONEY_STORAGE",
    "NumericPrecision",
    "PERCENTAGE_STORAGE",
    "QUANTITY_STORAGE",
    "RATE_STORAGE",
]
