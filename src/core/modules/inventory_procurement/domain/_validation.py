from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import TypeVar

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
)

ITEM_CATEGORY_TYPES = frozenset(
    {
        "CONSUMABLE",
        "SPARE",
        "EQUIPMENT",
        "TOOL",
        "CHEMICAL",
        "MATERIAL",
        "SERVICE",
        "OTHER",
    }
)

ITEM_STATUS_VALUES = frozenset({"DRAFT", "ACTIVE", "INACTIVE", "OBSOLETE"})
STOREROOM_STATUS_VALUES = frozenset({"DRAFT", "ACTIVE", "INACTIVE", "CLOSED"})

EnumT = TypeVar("EnumT", bound=Enum)


def _label_code(label: str, suffix: str) -> str:
    return f"{label.upper().replace(' ', '_')}_{suffix}"


def normalize_inventory_code(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    ).upper()


def normalize_inventory_name(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    )


def normalize_optional_upper_text(value: object) -> str:
    return normalize_optional_text(value).upper()


def normalize_optional_date(value: object, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = normalize_optional_text(value)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(
            f"{label} must use ISO date format YYYY-MM-DD.",
            code="INVENTORY_DATE_INVALID",
        ) from exc


def normalize_optional_datetime(
    value: object,
    *,
    message: str,
    code: str,
) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        resolved = value
    else:
        raw = normalize_optional_text(value)
        try:
            resolved = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError(message, code=code) from exc
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved.astimezone(timezone.utc)


def normalize_status(
    value: object,
    *,
    default_status: str,
    allowed_statuses: set[str] | frozenset[str],
    label: str,
) -> str:
    normalized = normalize_optional_upper_text(value) or default_status
    if normalized not in allowed_statuses:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_STATUS_INVALID")
    return normalized


def normalize_item_category_type(value: object, *, label: str = "Item category type") -> str:
    normalized = normalize_optional_upper_text(value) or "MATERIAL"
    if normalized not in ITEM_CATEGORY_TYPES:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_CATEGORY_TYPE_INVALID")
    return normalized


def normalize_uom(value: object, *, label: str) -> str:
    normalized = normalize_optional_upper_text(value)
    if not normalized:
        raise ValidationError(f"{label} is required.", code="INVENTORY_UOM_REQUIRED")
    return normalized


def normalize_nonnegative_quantity(value: object, *, label: str) -> float:
    try:
        amount = float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_QUANTITY_INVALID") from exc
    if amount < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_QUANTITY_INVALID")
    return amount


def normalize_optional_nonnegative_quantity(value: object, *, label: str) -> float | None:
    if value in (None, ""):
        return None
    return normalize_nonnegative_quantity(value, label=label)


def normalize_nonnegative_days(value: object, *, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_DAYS_INVALID") from exc
    if days < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_DAYS_INVALID")
    return days


def normalize_positive_int(
    value: object,
    *,
    message: str,
    code: str,
) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if normalized <= 0:
        raise ValidationError(message, code=code)
    return normalized


def normalize_enum(
    value: object,
    *,
    enum_type: type[EnumT],
    default: EnumT,
    message: str,
    code: str,
) -> EnumT:
    if isinstance(value, enum_type):
        return value
    raw = normalize_optional_upper_text(value)
    if not raw:
        return default
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise ValidationError(message, code=code) from exc


__all__ = [
    "ITEM_CATEGORY_TYPES",
    "ITEM_STATUS_VALUES",
    "STOREROOM_STATUS_VALUES",
    "normalize_enum",
    "normalize_inventory_code",
    "normalize_inventory_name",
    "normalize_item_category_type",
    "normalize_nonnegative_days",
    "normalize_nonnegative_quantity",
    "normalize_optional_date",
    "normalize_optional_datetime",
    "normalize_optional_identifier",
    "normalize_optional_nonnegative_quantity",
    "normalize_optional_text",
    "normalize_optional_upper_text",
    "normalize_positive_int",
    "normalize_required_text",
    "normalize_status",
    "normalize_uom",
]
