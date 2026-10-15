from __future__ import annotations

from decimal import Decimal, InvalidOperation

from src.core.platform.common.exceptions import ValidationError


def command_amount(value: str) -> Decimal:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            "Budget line amount must be a canonical decimal value.",
            code="PROJECT_BUDGET_LINE_AMOUNT_INVALID",
        ) from exc
    if not amount.is_finite():
        raise ValidationError(
            "Budget line amount must be finite.",
            code="PROJECT_BUDGET_LINE_AMOUNT_INVALID",
        )
    return amount
