from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import normalize_optional_text

_DEFAULT_SCORING_TEMPLATE_NAME = "Balanced PMO"


def _validate_portfolio_weight(value: object, *, label: str, code: str) -> int:
    resolved = int(value if value not in (None, "") else 0)
    if resolved < 0 or resolved > 9:
        raise ValidationError(
            f"{label} must be between 0 and 9.",
            code=code,
        )
    return resolved


def _validate_portfolio_score(value: object, *, label: str, code: str) -> int:
    resolved = int(value if value not in (None, "") else 0)
    if resolved < 1 or resolved > 5:
        raise ValidationError(
            f"{label} must be between 1 and 5.",
            code=code,
        )
    return resolved


def _validate_non_negative_float(value: object, *, label: str, code: str) -> float:
    resolved = float(value if value not in (None, "") else 0.0)
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=code,
        )
    return resolved


def _validate_optional_non_negative_float(
    value: object,
    *,
    label: str,
    code: str,
) -> float | None:
    if value in (None, ""):
        return None
    return _validate_non_negative_float(value, label=label, code=code)


def _validate_non_negative_decimal(value: object, *, label: str, code: str) -> Decimal:
    try:
        resolved = Decimal(str(value if value not in (None, "") else "0"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be a valid decimal value.", code=code) from exc
    if not resolved.is_finite() or resolved < 0:
        raise ValidationError(f"{label} cannot be negative.", code=code)
    return resolved


def _validate_optional_non_negative_decimal(
    value: object, *, label: str, code: str
) -> Decimal | None:
    if value in (None, ""):
        return None
    return _validate_non_negative_decimal(value, label=label, code=code)


def _normalize_identifier_list(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_values = [value]
    else:
        try:
            raw_values = list(value)
        except TypeError:
            raw_values = [value]
    normalized = {normalize_optional_text(item) for item in raw_values}
    return sorted(item for item in normalized if item)


def _validate_portfolio_date(value: object, *, message: str, code: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date):
        raise ValidationError(message, code=code)
    return value


def _validate_portfolio_datetime(value: object, *, message: str, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(message, code=code)
    return value
