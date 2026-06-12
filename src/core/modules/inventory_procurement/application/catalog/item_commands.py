from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.catalog.catalog_access import (
    _require_manage,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_audit import (
    record_inventory_item_create_audit,
    record_inventory_item_update_audit,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.catalog.item_category_resolver import (
    _resolve_category_reference,
)
from src.core.modules.inventory_procurement.application.catalog.item_validation import (
    _validate_party_reference,
    _validate_reorder_quantities,
    _validate_uom_configuration,
)
from src.core.modules.inventory_procurement.application.common.support import (
    ITEM_STATUS_TRANSITIONS,
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_nonnegative_days,
    normalize_nonnegative_quantity,
    normalize_optional_text,
    normalize_status,
    normalize_uom,
    resolve_active_flag_from_status,
    resolve_configured_uom_ratio,
    resolve_status_from_active,
    validate_transition,
)
from src.core.modules.inventory_procurement.domain.catalog.item import StockItem
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events


def create_item(
    owner: Any,
    *,
    item_code: str,
    name: str,
    description: str = "",
    item_type: str = "",
    status: str | None = None,
    stock_uom: str,
    order_uom: str | None = None,
    issue_uom: str | None = None,
    order_uom_ratio: float | None = None,
    issue_uom_ratio: float | None = None,
    category_code: str = "",
    commodity_code: str = "",
    is_stocked: bool = True,
    is_purchase_allowed: bool = True,
    default_reorder_policy: str = "",
    min_qty: float = 0.0,
    max_qty: float = 0.0,
    reorder_point: float = 0.0,
    reorder_qty: float = 0.0,
    lead_time_days: int | None = None,
    is_lot_tracked: bool = False,
    is_serial_tracked: bool = False,
    shelf_life_days: int | None = None,
    preferred_party_id: str | None = None,
    notes: str = "",
) -> StockItem:
    _require_manage(owner, "create inventory item")
    organization = _active_organization(owner)
    normalized_code = normalize_inventory_code(item_code, label="Item code")
    if owner._item_repo.get_by_code(organization.id, normalized_code) is not None:
        raise ValidationError(
            "Item code already exists in the active organization.",
            code="INVENTORY_ITEM_CODE_EXISTS",
        )
    normalized_stock_uom = normalize_uom(stock_uom, label="Stock UOM")
    normalized_order_uom = normalize_uom(order_uom or stock_uom, label="Order UOM")
    normalized_issue_uom = normalize_uom(issue_uom or stock_uom, label="Issue UOM")
    resolved_category_code, category = _resolve_category_reference(owner, category_code)
    normalized_item_type = normalize_optional_text(item_type).upper()
    if not normalized_item_type and category is not None:
        normalized_item_type = category.category_type
    resolved_status = normalize_status(
        status,
        default_status="DRAFT",
        allowed_statuses=set(ITEM_STATUS_TRANSITIONS.keys()),
        label="Inventory item status",
    )
    item = StockItem.create(
        organization_id=organization.id,
        item_code=normalized_code,
        name=normalize_inventory_name(name, label="Item name"),
        description=normalize_optional_text(description),
        item_type=normalized_item_type,
        status=resolved_status,
        stock_uom=normalized_stock_uom,
        order_uom=normalized_order_uom,
        issue_uom=normalized_issue_uom,
        order_uom_ratio=resolve_configured_uom_ratio(
            uom=normalized_order_uom,
            stock_uom=normalized_stock_uom,
            ratio=order_uom_ratio,
            label="Order",
        ),
        issue_uom_ratio=resolve_configured_uom_ratio(
            uom=normalized_issue_uom,
            stock_uom=normalized_stock_uom,
            ratio=issue_uom_ratio,
            label="Issue",
        ),
        category_code=resolved_category_code,
        commodity_code=normalize_optional_text(commodity_code).upper(),
        is_stocked=bool(is_stocked),
        is_purchase_allowed=bool(is_purchase_allowed),
        is_active=resolve_active_flag_from_status(resolved_status),
        default_reorder_policy=normalize_optional_text(default_reorder_policy).upper(),
        min_qty=normalize_nonnegative_quantity(min_qty, label="Minimum quantity"),
        max_qty=normalize_nonnegative_quantity(max_qty, label="Maximum quantity"),
        reorder_point=normalize_nonnegative_quantity(reorder_point, label="Reorder point"),
        reorder_qty=normalize_nonnegative_quantity(reorder_qty, label="Reorder quantity"),
        lead_time_days=normalize_nonnegative_days(lead_time_days, label="Lead time days"),
        is_lot_tracked=bool(is_lot_tracked),
        is_serial_tracked=bool(is_serial_tracked),
        shelf_life_days=normalize_nonnegative_days(
            shelf_life_days,
            label="Shelf life days",
        ),
        preferred_party_id=_validate_party_reference(owner, preferred_party_id),
        notes=normalize_optional_text(notes),
    )
    _validate_uom_configuration(item)
    _validate_reorder_quantities(item)
    try:
        owner._item_repo.add(item)
        owner._session.commit()
    except IntegrityError as exc:
        owner._session.rollback()
        raise ValidationError(
            "Item code already exists in the active organization.",
            code="INVENTORY_ITEM_CODE_EXISTS",
        ) from exc
    except Exception:
        owner._session.rollback()
        raise
    record_inventory_item_create_audit(
        owner,
        organization_id=organization.id,
        item=item,
    )
    domain_events.inventory_items_changed.emit(item.id)
    return item


def update_item(
    owner: Any,
    item_id: str,
    *,
    item_code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    item_type: str | None = None,
    status: str | None = None,
    is_stocked: bool | None = None,
    is_purchase_allowed: bool | None = None,
    stock_uom: str | None = None,
    order_uom: str | None = None,
    issue_uom: str | None = None,
    order_uom_ratio: float | None = None,
    issue_uom_ratio: float | None = None,
    category_code: str | None = None,
    commodity_code: str | None = None,
    default_reorder_policy: str | None = None,
    min_qty: float | None = None,
    max_qty: float | None = None,
    reorder_point: float | None = None,
    reorder_qty: float | None = None,
    lead_time_days: int | None = None,
    is_lot_tracked: bool | None = None,
    is_serial_tracked: bool | None = None,
    shelf_life_days: int | None = None,
    preferred_party_id: str | None = None,
    is_active: bool | None = None,
    notes: str | None = None,
    expected_version: int | None = None,
) -> StockItem:
    _require_manage(owner, "update inventory item")
    organization = _active_organization(owner)
    item = owner._item_repo.get(item_id)
    if item is None or item.organization_id != organization.id:
        raise NotFoundError(
            "Inventory item not found in the active organization.",
            code="INVENTORY_ITEM_NOT_FOUND",
        )
    if expected_version is not None and item.version != expected_version:
        raise ConcurrencyError(
            "Inventory item changed since you opened it. Refresh and try again.",
            code="STALE_WRITE",
        )
    previous_stock_uom = item.stock_uom
    if item_code is not None:
        normalized_code = normalize_inventory_code(item_code, label="Item code")
        existing = owner._item_repo.get_by_code(organization.id, normalized_code)
        if existing is not None and existing.id != item.id:
            raise ValidationError(
                "Item code already exists in the active organization.",
                code="INVENTORY_ITEM_CODE_EXISTS",
            )
        item.item_code = normalized_code
    if name is not None:
        item.name = normalize_inventory_name(name, label="Item name")
    if description is not None:
        item.description = normalize_optional_text(description)
    if item_type is not None:
        item.item_type = normalize_optional_text(item_type).upper()
    if stock_uom is not None:
        item.stock_uom = normalize_uom(stock_uom, label="Stock UOM")
    if order_uom is not None:
        item.order_uom = normalize_uom(order_uom, label="Order UOM")
    elif (
        stock_uom is not None
        and normalize_optional_text(item.order_uom).upper() == previous_stock_uom
    ):
        item.order_uom = item.stock_uom
    if issue_uom is not None:
        item.issue_uom = normalize_uom(issue_uom, label="Issue UOM")
    elif (
        stock_uom is not None
        and normalize_optional_text(item.issue_uom).upper() == previous_stock_uom
    ):
        item.issue_uom = item.stock_uom
    if stock_uom is not None and item.order_uom != item.stock_uom and order_uom_ratio is None:
        raise ValidationError(
            "Order UOM factor must be provided when stock UOM changes and order UOM remains different.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    if stock_uom is not None and item.issue_uom != item.stock_uom and issue_uom_ratio is None:
        raise ValidationError(
            "Issue UOM factor must be provided when stock UOM changes and issue UOM remains different.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    item.order_uom_ratio = resolve_configured_uom_ratio(
        uom=item.order_uom,
        stock_uom=item.stock_uom,
        ratio=(
            order_uom_ratio
            if order_uom_ratio is not None
            else item.order_uom_ratio
        ),
        label="Order",
    )
    item.issue_uom_ratio = resolve_configured_uom_ratio(
        uom=item.issue_uom,
        stock_uom=item.stock_uom,
        ratio=(
            issue_uom_ratio
            if issue_uom_ratio is not None
            else item.issue_uom_ratio
        ),
        label="Issue",
    )
    if category_code is not None:
        resolved_category_code, _category = _resolve_category_reference(
            owner,
            category_code,
            allow_existing_code=item.category_code,
        )
        item.category_code = resolved_category_code
    if commodity_code is not None:
        item.commodity_code = normalize_optional_text(commodity_code).upper()
    if is_stocked is not None:
        item.is_stocked = bool(is_stocked)
    if is_purchase_allowed is not None:
        item.is_purchase_allowed = bool(is_purchase_allowed)
    if default_reorder_policy is not None:
        item.default_reorder_policy = normalize_optional_text(default_reorder_policy).upper()
    if min_qty is not None:
        item.min_qty = normalize_nonnegative_quantity(min_qty, label="Minimum quantity")
    if max_qty is not None:
        item.max_qty = normalize_nonnegative_quantity(max_qty, label="Maximum quantity")
    if reorder_point is not None:
        item.reorder_point = normalize_nonnegative_quantity(
            reorder_point,
            label="Reorder point",
        )
    if reorder_qty is not None:
        item.reorder_qty = normalize_nonnegative_quantity(
            reorder_qty,
            label="Reorder quantity",
        )
    if lead_time_days is not None:
        item.lead_time_days = normalize_nonnegative_days(
            lead_time_days,
            label="Lead time days",
        )
    if is_lot_tracked is not None:
        item.is_lot_tracked = bool(is_lot_tracked)
    if is_serial_tracked is not None:
        item.is_serial_tracked = bool(is_serial_tracked)
    if shelf_life_days is not None:
        item.shelf_life_days = normalize_nonnegative_days(
            shelf_life_days,
            label="Shelf life days",
        )
    if preferred_party_id is not None:
        item.preferred_party_id = _validate_party_reference(owner, preferred_party_id)
    next_status = item.status
    if status is not None:
        next_status = normalize_status(
            status,
            default_status=item.status,
            allowed_statuses=set(ITEM_STATUS_TRANSITIONS.keys()),
            label="Inventory item status",
        )
        validate_transition(
            current_status=item.status,
            next_status=next_status,
            transitions=ITEM_STATUS_TRANSITIONS,
        )
    elif is_active is not None:
        next_status = resolve_status_from_active(
            current_status=item.status,
            is_active=bool(is_active),
            transitions=ITEM_STATUS_TRANSITIONS,
        )
    item.status = next_status
    item.is_active = resolve_active_flag_from_status(item.status)
    if notes is not None:
        item.notes = normalize_optional_text(notes)
    _validate_uom_configuration(item)
    _validate_reorder_quantities(item)
    item.updated_at = datetime.now(timezone.utc)
    try:
        owner._item_repo.update(item)
        owner._session.commit()
    except IntegrityError as exc:
        owner._session.rollback()
        raise ValidationError(
            "Item code already exists in the active organization.",
            code="INVENTORY_ITEM_CODE_EXISTS",
        ) from exc
    except Exception:
        owner._session.rollback()
        raise
    record_inventory_item_update_audit(
        owner,
        organization_id=organization.id,
        item=item,
    )
    domain_events.inventory_items_changed.emit(item.id)
    return item


__all__ = ["create_item", "update_item"]
