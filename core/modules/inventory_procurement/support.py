from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from core.modules.inventory_procurement.domain import StockItem
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.org.support import normalize_code, normalize_name
from src.core.platform.party.domain import PartyType

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

ITEM_CATEGORY_TYPES = {
    "CONSUMABLE",
    "SPARE",
    "EQUIPMENT",
    "TOOL",
    "CHEMICAL",
    "MATERIAL",
    "SERVICE",
    "OTHER",
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

PURCHASE_ORDER_STATUS_TRANSITIONS = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"UNDER_REVIEW", "APPROVED", "REJECTED", "CANCELLED"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"SENT", "PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CANCELLED", "CLOSED"},
    "SENT": {"PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CANCELLED", "CLOSED"},
    "PARTIALLY_RECEIVED": {"FULLY_RECEIVED", "CLOSED", "CANCELLED"},
    "FULLY_RECEIVED": {"CLOSED"},
    "REJECTED": set(),
    "CANCELLED": set(),
    "CLOSED": set(),
}

RESERVATION_STATUS_TRANSITIONS = {
    "ACTIVE": {"PARTIALLY_ISSUED", "FULLY_ISSUED", "RELEASED", "CANCELLED"},
    "PARTIALLY_ISSUED": {"FULLY_ISSUED", "RELEASED"},
    "FULLY_ISSUED": set(),
    "RELEASED": set(),
    "CANCELLED": set(),
}

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


def normalize_inventory_code(value: str, *, label: str) -> str:
    return normalize_code(value, label=label)


def normalize_inventory_name(value: str | None, *, label: str) -> str:
    return normalize_name(value, label=label)


def normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def normalize_optional_date(value: date | str | None, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    normalized = normalize_optional_text(str(value))
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{label} must use ISO date format YYYY-MM-DD.",
            code="INVENTORY_DATE_INVALID",
        ) from exc


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


def normalize_item_category_type(value: str | None, *, label: str = "Item category type") -> str:
    normalized = normalize_optional_text(value).upper() or "MATERIAL"
    if normalized not in ITEM_CATEGORY_TYPES:
        raise ValidationError(f"{label} is invalid.", code="INVENTORY_CATEGORY_TYPE_INVALID")
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


def resolve_configured_uom_ratio(
    *,
    uom: str,
    stock_uom: str,
    ratio: float | int | None,
    label: str,
) -> float:
    normalized_stock_uom = normalize_uom(stock_uom, label="Stock UOM")
    normalized_uom = normalize_uom(uom, label=f"{label} UOM")
    if normalized_uom == normalized_stock_uom:
        return 1.0
    if ratio is None:
        raise ValidationError(
            f"{label} UOM factor is required when {label.lower()} UOM differs from stock UOM.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    factor = float(ratio)
    if factor <= 0:
        raise ValidationError(
            f"{label} UOM factor must be greater than zero.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    return factor


def resolve_item_uom_factor(item: StockItem, uom: str, *, label: str) -> float:
    normalized_uom = normalize_uom(uom, label=label)
    if normalized_uom == item.stock_uom:
        return 1.0
    if normalized_uom == item.order_uom:
        return resolve_configured_uom_ratio(
            uom=item.order_uom,
            stock_uom=item.stock_uom,
            ratio=item.order_uom_ratio,
            label="Order",
        )
    if normalized_uom == item.issue_uom:
        return resolve_configured_uom_ratio(
            uom=item.issue_uom,
            stock_uom=item.stock_uom,
            ratio=item.issue_uom_ratio,
            label="Issue",
        )
    raise ValidationError(
        f"{label} must match the item's configured stock UOM or supported order/issue UOM.",
        code="INVENTORY_UOM_CONVERSION_REQUIRED",
    )


def convert_item_quantity(
    item: StockItem,
    quantity: float,
    *,
    from_uom: str,
    to_uom: str,
    label: str,
) -> float:
    from_factor = resolve_item_uom_factor(item, from_uom, label=label)
    to_factor = resolve_item_uom_factor(item, to_uom, label=label)
    stock_quantity = float(quantity) * from_factor
    return stock_quantity / to_factor


def convert_item_unit_cost_to_stock(
    item: StockItem,
    unit_cost: float,
    *,
    uom: str,
    label: str,
) -> float:
    factor = resolve_item_uom_factor(item, uom, label=label)
    return normalize_nonnegative_quantity(unit_cost, label=label) / factor


def normalize_nonnegative_days(value: int | None, *, label: str) -> int | None:
    if value is None:
        return None
    days = int(value)
    if days < 0:
        raise ValidationError(f"{label} cannot be negative.", code="INVENTORY_DAYS_INVALID")
    return days


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


def validate_receipt_tracking(
    *,
    item: StockItem,
    accepted_quantity: float,
    lot_number: str,
    serial_number: str,
    expiry_date: date | None,
    receipt_date: datetime,
) -> None:
    if accepted_quantity <= 0:
        return
    if item.is_lot_tracked and not lot_number:
        raise ValidationError(
            "Lot-tracked items require a lot number when quantity is accepted.",
            code="INVENTORY_RECEIPT_LOT_REQUIRED",
        )
    if item.is_serial_tracked:
        if not serial_number:
            raise ValidationError(
                "Serial-tracked items require a serial number when quantity is accepted.",
                code="INVENTORY_RECEIPT_SERIAL_REQUIRED",
            )
        if abs(float(accepted_quantity) - 1.0) > 1e-9:
            raise ValidationError(
                "Serial-tracked items must be received one serial number at a time.",
                code="INVENTORY_RECEIPT_SERIAL_QTY_INVALID",
            )
    if item.shelf_life_days is not None:
        if expiry_date is None:
            raise ValidationError(
                "Shelf-life-controlled items require an expiry date when quantity is accepted.",
                code="INVENTORY_RECEIPT_EXPIRY_REQUIRED",
            )
        received_on = receipt_date.astimezone(timezone.utc).date()
        minimum_expiry = received_on + timedelta(days=max(0, int(item.shelf_life_days or 0)))
        if expiry_date < minimum_expiry:
            raise ValidationError(
                "Expiry date does not satisfy the configured shelf-life window.",
                code="INVENTORY_RECEIPT_EXPIRY_INVALID",
            )


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
    "ITEM_CATEGORY_TYPES",
    "INVENTORY_SOURCE_REFERENCE_TYPES",
    "MAINTENANCE_SOURCE_REFERENCE_TYPES",
    "PURCHASE_ORDER_STATUS_TRANSITIONS",
    "REQUISITION_STATUS_TRANSITIONS",
    "RESERVATION_STATUS_TRANSITIONS",
    "STOREROOM_STATUS_TRANSITIONS",
    "normalize_inventory_code",
    "normalize_inventory_name",
    "normalize_item_category_type",
    "normalize_optional_date",
    "normalize_nonnegative_days",
    "normalize_nonnegative_quantity",
    "normalize_positive_quantity",
    "normalize_optional_text",
    "normalize_maintenance_source_reference_type",
    "normalize_source_reference_type",
    "normalize_status",
    "normalize_uom",
    "validate_receipt_tracking",
    "convert_item_quantity",
    "convert_item_unit_cost_to_stock",
    "resolve_configured_uom_ratio",
    "resolve_item_uom_factor",
    "resolve_active_flag_from_status",
    "resolve_status_from_active",
    "validate_transition",
]
