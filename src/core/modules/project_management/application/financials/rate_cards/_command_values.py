from __future__ import annotations

from decimal import Decimal, InvalidOperation

from src.core.platform.common.exceptions import ValidationError


def command_amount(value: str, label: str) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"{label} must be a canonical decimal value.",
            code="RATE_CARD_DECIMAL_INVALID",
        ) from exc
    if not amount.is_finite():
        raise ValidationError(
            f"{label} must be finite.", code="RATE_CARD_DECIMAL_INVALID"
        )
    return amount


def optional_command_amount(value: str | None) -> Decimal | None:
    return None if value in (None, "") else command_amount(value, "Rate modifier")
