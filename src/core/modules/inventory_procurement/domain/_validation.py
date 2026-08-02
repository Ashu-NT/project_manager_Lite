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
PROCUREMENT_PRIORITY_VALUES = frozenset({"LOW", "NORMAL", "HIGH", "URGENT"})
INVENTORY_SOURCE_REFERENCE_TYPES: tuple[str, ...] = (
    "task",
    "work_order",
    "maintenance_task",
    "maintenance_work_order",
    "maintenance_request",
    "maintenance_operation",
    "maintenance_plan",
    "maintenance_material_demand",
    "reservation",
    "requisition",
    "purchase_order",
)
MAINTENANCE_SOURCE_REFERENCE_TYPES: tuple[str, ...] = (
    "maintenance_task",
    "maintenance_work_order",
    "maintenance_request",
    "maintenance_operation",
    "maintenance_plan",
    "maintenance_material_demand",
)

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


def normalize_procurement_priority(value: object) -> str:
    normalized = normalize_optional_upper_text(value) or "NORMAL"
    if normalized not in PROCUREMENT_PRIORITY_VALUES:
        raise ValidationError(
            "Procurement priority is invalid.",
            code="INVENTORY_PROCUREMENT_PRIORITY_INVALID",
        )
    return normalized


def normalize_currency_code(value: object, *, fallback: object = "") -> str:
    normalized = normalize_optional_upper_text(value) or normalize_optional_upper_text(fallback)
    if not normalized:
        raise ValidationError("Currency code is required.", code="INVENTORY_CURRENCY_REQUIRED")
    return normalized


def normalize_nonnegative_quantity(value: object, *, label: str) -> float:
    try:
        amount = float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_QUANTITY_INVALID") from exc
    if amount < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_QUANTITY_INVALID")
    return amount


def normalize_positive_quantity(value: object, *, label: str) -> float:
    amount = normalize_nonnegative_quantity(value, label=label)
    if amount <= 0:
        raise ValidationError(
            f"{label} must be greater than zero.",
            code="INVENTORY_QUANTITY_REQUIRED",
        )
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


def normalize_source_reference_type(value: str | None) -> str:
    normalized = normalize_optional_text(value).lower()
    if not normalized:
        return ""
    if normalized not in INVENTORY_SOURCE_REFERENCE_TYPES:
        raise ValidationError(
            "Source reference type is invalid.",
            code="INVENTORY_SOURCE_REFERENCE_TYPE_INVALID",
        )
    return normalized


def normalize_maintenance_source_reference_type(value: str | None) -> str:
    normalized = normalize_optional_text(value).lower()
    if not normalized:
        raise ValidationError(
            "Maintenance source reference type is required.",
            code="INVENTORY_MAINTENANCE_SOURCE_REFERENCE_REQUIRED",
        )
    if normalized not in MAINTENANCE_SOURCE_REFERENCE_TYPES:
        raise ValidationError(
            "Maintenance source reference type is invalid.",
            code="INVENTORY_MAINTENANCE_SOURCE_REFERENCE_INVALID",
        )
    return normalized


__all__ = [
    "ITEM_CATEGORY_TYPES",
    "ITEM_STATUS_VALUES",
    "INVENTORY_SOURCE_REFERENCE_TYPES",
    "MAINTENANCE_SOURCE_REFERENCE_TYPES",
    "PROCUREMENT_PRIORITY_VALUES",
    "STOREROOM_STATUS_VALUES",
    "normalize_currency_code",
    "normalize_enum",
    "normalize_inventory_code",
    "normalize_inventory_name",
    "normalize_maintenance_source_reference_type",
    "normalize_item_category_type",
    "normalize_nonnegative_days",
    "normalize_nonnegative_quantity",
    "normalize_optional_date",
    "normalize_optional_datetime",
    "normalize_optional_identifier",
    "normalize_optional_nonnegative_quantity",
    "normalize_optional_text",
    "normalize_optional_upper_text",
    "normalize_procurement_priority",
    "normalize_positive_int",
    "normalize_positive_quantity",
    "normalize_required_text",
    "normalize_source_reference_type",
    "normalize_status",
    "normalize_uom",
]
