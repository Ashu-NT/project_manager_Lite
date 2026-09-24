from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
    localcontext,
)
from enum import Enum

from src.core.platform.common.exceptions import ValidationError

from ._decimal import DecimalInput, decimal_value


class RoundingMode(str, Enum):
    HALF_EVEN = ROUND_HALF_EVEN
    HALF_UP = ROUND_HALF_UP
    HALF_DOWN = ROUND_HALF_DOWN
    DOWN = ROUND_DOWN
    UP = ROUND_UP
    FLOOR = ROUND_FLOOR
    CEILING = ROUND_CEILING


@dataclass(frozen=True, slots=True)
class RoundingPolicy:
    mode: RoundingMode = RoundingMode.HALF_EVEN

    def __post_init__(self) -> None:
        if not isinstance(self.mode, RoundingMode):
            try:
                object.__setattr__(self, "mode", RoundingMode(str(self.mode)))
            except ValueError as exc:
                raise ValidationError(
                    "Rounding mode is invalid.",
                    code="ROUNDING_MODE_INVALID",
                ) from exc

    def quantize(self, value: DecimalInput, *, scale: int) -> Decimal:
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0 or scale > 18:
            raise ValidationError(
                "Rounding scale must be an integer from 0 through 18.",
                code="ROUNDING_SCALE_INVALID",
            )
        resolved = decimal_value(value)
        quantum = Decimal("1").scaleb(-scale)
        digits = len(resolved.as_tuple().digits)
        with localcontext() as context:
            context.prec = max(34, digits + abs(resolved.adjusted()) + scale + 4)
            return resolved.quantize(quantum, rounding=self.mode.value)


DEFAULT_ROUNDING_POLICY = RoundingPolicy()


__all__ = ["DEFAULT_ROUNDING_POLICY", "RoundingMode", "RoundingPolicy"]
