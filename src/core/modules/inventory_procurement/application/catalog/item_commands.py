from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.catalog.catalog_access import (
    _require_manage,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_activity import (
    record_inventory_item_create_activity,
    record_inventory_item_update_activity,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.catalog.item_category_resolver import (
    _resolve_category_reference,
)
from src.core.modules.inventory_procurement.application.catalog.item_validation import (
    _validate_party_reference,
)
from src.core.modules.inventory_procurement.application.common.support import (
    ITEM_STATUS_TRANSITIONS,
    normalize_inventory_code,
    normalize_optional_text,
    normalize_status,
    normalize_uom,
    resolve_status_from_active,
    validate_transition,
)
from src.core.modules.inventory_procurement.domain.catalog.catalog_events import (
    InventoryItemCreated,
    InventoryItemProfileUpdated,
    InventoryItemStatusChanged,
)
from src.core.modules.inventory_procurement.domain.catalog.item import StockItem
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.audit import record_audit_entry


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
    item = StockItem.create(
        organization_id=organization.id,
        item_code=normalized_code,
        name=name,
        description=description,
        item_type=normalized_item_type,
        status=status,
        stock_uom=normalized_stock_uom,
        order_uom=order_uom or normalized_order_uom,
        issue_uom=issue_uom or normalized_issue_uom,
        order_uom_ratio=order_uom_ratio,
        issue_uom_ratio=issue_uom_ratio,
        category_code=resolved_category_code,
        commodity_code=commodity_code,
        is_stocked=bool(is_stocked),
        is_purchase_allowed=bool(is_purchase_allowed),
        default_reorder_policy=default_reorder_policy,
        min_qty=min_qty,
        max_qty=max_qty,
        reorder_point=reorder_point,
        reorder_qty=reorder_qty,
        lead_time_days=lead_time_days,
        is_lot_tracked=bool(is_lot_tracked),
        is_serial_tracked=bool(is_serial_tracked),
        shelf_life_days=shelf_life_days,
        preferred_party_id=_validate_party_reference(owner, preferred_party_id),
        notes=notes,
    )
    now = datetime.now(timezone.utc)
    uow = owner._require_uow_factory().create(context=owner._new_context())
    with uow:
        try:
            uow.items.add(item)
        except IntegrityError as exc:
            raise ValidationError(
                "Item code already exists in the active organization.",
                code="INVENTORY_ITEM_CODE_EXISTS",
            ) from exc
        record_inventory_item_create_activity(
            uow,
            organization_id=organization.id,
            item=item,
            commit=False,
        )
        record_audit_entry(
            uow,
            operation="create",
            entity_type="inventory_item",
            entity_id=item.id,
            module="inventory_procurement",
            organization_id=organization.id,
            severity="low",
            metadata={
                "item_code": item.item_code,
                "name": item.name,
                "status": item.status,
            },
            commit=False,
            fail_closed=True,
        )
        uow.record_event(
            InventoryItemCreated(
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                item_id=item.id,
                occurred_at=now,
            )
        )
        uow.commit()
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
    next_item_code = item.item_code
    if item_code is not None:
        next_item_code = normalize_inventory_code(item_code, label="Item code")
        existing = owner._item_repo.get_by_code(organization.id, next_item_code)
        if existing is not None and existing.id != item.id:
            raise ValidationError(
                "Item code already exists in the active organization.",
                code="INVENTORY_ITEM_CODE_EXISTS",
            )
    next_stock_uom = item.stock_uom if stock_uom is None else normalize_uom(stock_uom, label="Stock UOM")
    next_order_uom = item.order_uom
    if order_uom is not None:
        next_order_uom = normalize_uom(order_uom, label="Order UOM")
    elif stock_uom is not None and item.order_uom == previous_stock_uom:
        next_order_uom = next_stock_uom
    next_issue_uom = item.issue_uom
    if issue_uom is not None:
        next_issue_uom = normalize_uom(issue_uom, label="Issue UOM")
    elif stock_uom is not None and item.issue_uom == previous_stock_uom:
        next_issue_uom = next_stock_uom
    if stock_uom is not None and next_order_uom != next_stock_uom and order_uom_ratio is None:
        raise ValidationError(
            "Order UOM factor must be provided when stock UOM changes and order UOM remains different.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    if stock_uom is not None and next_issue_uom != next_stock_uom and issue_uom_ratio is None:
        raise ValidationError(
            "Issue UOM factor must be provided when stock UOM changes and issue UOM remains different.",
            code="INVENTORY_UOM_FACTOR_REQUIRED",
        )
    next_category_code = item.category_code
    if category_code is not None:
        next_category_code, _category = _resolve_category_reference(
            owner,
            category_code,
            allow_existing_code=item.category_code,
        )
    next_preferred_party_id = item.preferred_party_id
    if preferred_party_id is not None:
        next_preferred_party_id = _validate_party_reference(owner, preferred_party_id)
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
    candidate = replace(
        item,
        item_code=next_item_code,
        name=item.name if name is None else name,
        description=item.description if description is None else description,
        item_type=item.item_type if item_type is None else item_type,
        status=next_status,
        stock_uom=next_stock_uom,
        order_uom=next_order_uom,
        issue_uom=next_issue_uom,
        order_uom_ratio=(
            item.order_uom_ratio if order_uom_ratio is None else order_uom_ratio
        ),
        issue_uom_ratio=(
            item.issue_uom_ratio if issue_uom_ratio is None else issue_uom_ratio
        ),
        category_code=next_category_code,
        commodity_code=item.commodity_code if commodity_code is None else commodity_code,
        is_stocked=item.is_stocked if is_stocked is None else bool(is_stocked),
        is_purchase_allowed=(
            item.is_purchase_allowed
            if is_purchase_allowed is None
            else bool(is_purchase_allowed)
        ),
        default_reorder_policy=(
            item.default_reorder_policy
            if default_reorder_policy is None
            else default_reorder_policy
        ),
        min_qty=item.min_qty if min_qty is None else min_qty,
        max_qty=item.max_qty if max_qty is None else max_qty,
        reorder_point=item.reorder_point if reorder_point is None else reorder_point,
        reorder_qty=item.reorder_qty if reorder_qty is None else reorder_qty,
        lead_time_days=item.lead_time_days if lead_time_days is None else lead_time_days,
        is_lot_tracked=item.is_lot_tracked if is_lot_tracked is None else bool(is_lot_tracked),
        is_serial_tracked=(
            item.is_serial_tracked if is_serial_tracked is None else bool(is_serial_tracked)
        ),
        shelf_life_days=(
            item.shelf_life_days if shelf_life_days is None else shelf_life_days
        ),
        preferred_party_id=next_preferred_party_id,
        notes=item.notes if notes is None else notes,
    )
    if candidate == item:
        # True no-op (P24 §7): zero repository write, zero audit, zero typed event, no
        # synthetic version/updated_at bump.
        return item
    status_changed = candidate.status != item.status
    profile_changed = (
        candidate.item_code != item.item_code
        or candidate.name != item.name
        or candidate.description != item.description
        or candidate.item_type != item.item_type
        or candidate.stock_uom != item.stock_uom
        or candidate.order_uom != item.order_uom
        or candidate.issue_uom != item.issue_uom
        or candidate.order_uom_ratio != item.order_uom_ratio
        or candidate.issue_uom_ratio != item.issue_uom_ratio
        or candidate.category_code != item.category_code
        or candidate.commodity_code != item.commodity_code
        or candidate.is_stocked != item.is_stocked
        or candidate.is_purchase_allowed != item.is_purchase_allowed
        or candidate.default_reorder_policy != item.default_reorder_policy
        or candidate.min_qty != item.min_qty
        or candidate.max_qty != item.max_qty
        or candidate.reorder_point != item.reorder_point
        or candidate.reorder_qty != item.reorder_qty
        or candidate.lead_time_days != item.lead_time_days
        or candidate.is_lot_tracked != item.is_lot_tracked
        or candidate.is_serial_tracked != item.is_serial_tracked
        or candidate.shelf_life_days != item.shelf_life_days
        or candidate.preferred_party_id != item.preferred_party_id
        or candidate.notes != item.notes
    )
    now = datetime.now(timezone.utc)
    candidate = replace(candidate, updated_at=now)
    uow = owner._require_uow_factory().create(context=owner._new_context())
    with uow:
        try:
            uow.items.update(candidate)
        except IntegrityError as exc:
            raise ValidationError(
                "Item code already exists in the active organization.",
                code="INVENTORY_ITEM_CODE_EXISTS",
            ) from exc
        record_inventory_item_update_activity(
            uow,
            organization_id=organization.id,
            item=candidate,
            commit=False,
        )
        record_audit_entry(
            uow,
            operation="update",
            entity_type="inventory_item",
            entity_id=candidate.id,
            module="inventory_procurement",
            organization_id=organization.id,
            severity="low",
            metadata={
                "item_code": candidate.item_code,
                "name": candidate.name,
                "status": candidate.status,
            },
            commit=False,
            fail_closed=True,
        )
        if profile_changed:
            uow.record_event(
                InventoryItemProfileUpdated(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    item_id=candidate.id,
                    occurred_at=now,
                )
            )
        if status_changed:
            uow.record_event(
                InventoryItemStatusChanged(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    item_id=candidate.id,
                    status=candidate.status,
                    occurred_at=now,
                )
            )
        uow.commit()
    return candidate


__all__ = ["create_item", "update_item"]
