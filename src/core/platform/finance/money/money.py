from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, localcontext
from typing import Iterable

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError

from ._decimal import DecimalInput, decimal_from_legacy_float, decimal_value
from .currency import CurrencyCode
from .rounding import DEFAULT_ROUNDING_POLICY, RoundingPolicy


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: CurrencyCode

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", decimal_value(self.amount, label="Money amount"))
        object.__setattr__(self, "currency", CurrencyCode.parse(self.currency))

    @classmethod
    def of(cls, amount: DecimalInput, currency: CurrencyCode | str) -> Money:
        return cls(amount=amount, currency=currency)

    @classmethod
    def zero(cls, currency: CurrencyCode | str) -> Money:
        return cls(amount=Decimal("0"), currency=currency)

    @classmethod
    def from_legacy_float(cls, amount: float, currency: CurrencyCode | str) -> Money:
        # TRANSITION(PF-A1-LEGACY-FLOAT): Deterministic migration input only.
        # Temporary float conversion remains until monetary float columns are retired.
        return cls(
            amount=decimal_from_legacy_float(amount, label="Legacy money amount"),
            currency=currency,
        )

    def _require_same_currency(self, other: Money) -> None:
        if not isinstance(other, Money) or self.currency != other.currency:
            other_code = getattr(getattr(other, "currency", None), "code", "unknown")
            raise BusinessRuleError(
                f"Cannot combine {self.currency.code} and {other_code} money values.",
                code="MONEY_CURRENCY_MISMATCH",
            )

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __mul__(self, scalar: DecimalInput) -> Money:
        return Money(self.amount * decimal_value(scalar, label="Money multiplier"), self.currency)

    def __rmul__(self, scalar: DecimalInput) -> Money:
        return self * scalar

    def __truediv__(self, divisor: DecimalInput) -> Money:
        resolved = decimal_value(divisor, label="Money divisor")
        if resolved.is_zero():
            raise ValidationError("Money divisor cannot be zero.", code="MONEY_DIVISION_BY_ZERO")
        return Money(self.amount / resolved, self.currency)

    def rounded(self, policy: RoundingPolicy = DEFAULT_ROUNDING_POLICY) -> Money:
        minor_units = self.currency.minor_units
        if minor_units is None:
            self.currency.minor_unit_quantum()
        return Money(policy.quantize(self.amount, scale=minor_units), self.currency)

    def allocate(
        self,
        weights: Iterable[DecimalInput],
        *,
        policy: RoundingPolicy = DEFAULT_ROUNDING_POLICY,
    ) -> tuple[Money, ...]:
        resolved_weights = tuple(
            decimal_value(weight, label="Allocation weight") for weight in weights
        )
        if not resolved_weights:
            raise ValidationError(
                "At least one allocation weight is required.",
                code="MONEY_ALLOCATION_EMPTY",
            )
        if any(weight < 0 for weight in resolved_weights):
            raise ValidationError(
                "Allocation weights cannot be negative.",
                code="MONEY_ALLOCATION_WEIGHT_NEGATIVE",
            )
        total_weight = sum(resolved_weights, Decimal("0"))
        if total_weight.is_zero():
            raise ValidationError(
                "At least one allocation weight must be positive.",
                code="MONEY_ALLOCATION_WEIGHT_ZERO",
            )

        target = self.rounded(policy)
        quantum = target.currency.minor_unit_quantum()
        precision = max(34, len(target.amount.as_tuple().digits) + 24)
        with localcontext() as context:
            context.prec = precision
            raw = tuple(target.amount * weight / total_weight for weight in resolved_weights)
            allocated = [value.quantize(quantum, rounding=ROUND_DOWN) for value in raw]

        remainder_steps = int((target.amount - sum(allocated, Decimal("0"))) / quantum)
        if remainder_steps:
            residuals = [value - base for value, base in zip(raw, allocated, strict=True)]
            if remainder_steps > 0:
                indexes = sorted(
                    range(len(allocated)),
                    key=lambda index: (-residuals[index], index),
                )
            else:
                indexes = sorted(
                    range(len(allocated)),
                    key=lambda index: (residuals[index], index),
                )
            adjustment = quantum if remainder_steps > 0 else -quantum
            for index in indexes[: abs(remainder_steps)]:
                allocated[index] += adjustment

        return tuple(Money(amount, self.currency) for amount in allocated)


__all__ = ["Money"]
