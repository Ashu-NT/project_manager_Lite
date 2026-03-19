from __future__ import annotations

from core.platform.common.exceptions import ValidationError
from core.platform.org.support import normalize_code, normalize_name
from core.platform.party.domain import PartyType

BUSINESS_PARTY_TYPES = {
    PartyType.SUPPLIER,
    PartyType.MANUFACTURER,
    PartyType.VENDOR,
    PartyType.CONTRACTOR,
    PartyType.SERVICE_PROVIDER,
}

ITEM_STATUS_TRANSITIONS = {
    "DRAFT": {"ACTIVE"},
    "ACTIVE": {"INACTIVE", "OBSOLETE"},
    "INACTIVE": {"ACTIVE"},
    "OBSOLETE": set(),
}

STOREROOM_STATUS_TRANSITIONS = {
    "DRAFT": {"ACTIVE"},
    "ACTIVE": {"INACTIVE", "CLOSED"},
    "INACTIVE": {"ACTIVE"},
    "CLOSED": set(),
}

REQUISITION_STATUS_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"UNDER_REVIEW", "APPROVED", "REJECTED", "CANCELLED"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"PARTIALLY_SOURCED", "FULLY_SOURCED", "CANCELLED"},
    "PARTIALLY_SOURCED": {"FULLY_SOURCED", "CANCELLED"},
    "FULLY_SOURCED": {"CLOSED"},
    "REJECTED": set(),
    "CANCELLED": set(),
    "CLOSED": set(),
}


def normalize_inventory_code(value: str, *, label: str) -> str:
    return normalize_code(value, label=label)


def normalize_inventory_name(value: str | None, *, label: str) -> str:
    return normalize_name(value, label=label)


def normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def normalize_uom(value: str | None, *, label: str) -> str:
    normalized = normalize_optional_text(value).upper()
    if not normalized:
        raise ValidationError(f"{label} is required.", code="INVENTORY_UOM_REQUIRED")
    return normalized


def normalize_status(
    value: str | None,
    *,
    default_status: str,
    allowed_statuses: set[str],
    label: str,
) -> str:
    normalized = normalize_optional_text(value).upper() or default_status
    if normalized not in allowed_statuses:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_STATUS_INVALID")
    return normalized


def normalize_nonnegative_quantity(value: float | int | None, *, label: str) -> float:
    amount = float(value or 0.0)
    if amount < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_QUANTITY_INVALID")
    return amount


def normalize_positive_quantity(value: float | int | None, *, label: str) -> float:
    amount = float(value or 0.0)
    if amount <= 0:
        raise ValidationError(f"{label} must be greater than zero.", code="INVENTORY_QUANTITY_REQUIRED")
    return amount


def normalize_nonnegative_days(value: int | None, *, label: str) -> int | None:
    if value is None:
        return None
    days = int(value)
    if days < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_DAYS_INVALID")
    return days


def resolve_active_flag_from_status(status: str) -> bool:
    return status == "ACTIVE"


def resolve_status_from_active(
    *,
    current_status: str,
    is_active: bool,
    transitions: dict[str, set[str]],
) -> str:
    if is_active:
        candidate = "ACTIVE"
    elif current_status == "ACTIVE":
        candidate = "INACTIVE"
    else:
        candidate = current_status
    if candidate != current_status:
        validate_transition(current_status=current_status, next_status=candidate, transitions=transitions)
    return candidate


def validate_transition(
    *,
    current_status: str,
    next_status: str,
    transitions: dict[str, set[str]],
) -> None:
    if next_status == current_status:
        return
    allowed = transitions.get(current_status, set())
    if next_status not in allowed:
        raise ValidationError(
            f"Status transition {current_status} -> {next_status} is not allowed.",
            code="INVENTORY_STATUS_TRANSITION_INVALID",
        )


__all__ = [
    "BUSINESS_PARTY_TYPES",
    "ITEM_STATUS_TRANSITIONS",
    "REQUISITION_STATUS_TRANSITIONS",
    "STOREROOM_STATUS_TRANSITIONS",
    "normalize_inventory_code",
    "normalize_inventory_name",
    "normalize_nonnegative_days",
    "normalize_nonnegative_quantity",
    "normalize_positive_quantity",
    "normalize_optional_text",
    "normalize_status",
    "normalize_uom",
    "resolve_active_flag_from_status",
    "resolve_status_from_active",
    "validate_transition",
]
