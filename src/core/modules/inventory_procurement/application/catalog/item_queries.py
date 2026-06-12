from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.catalog.catalog_access import (
    _require_read,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.common.support import (
    normalize_inventory_code,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
    StockItem,
)
from src.core.platform.common.exceptions import NotFoundError


def list_items(owner: Any, *, active_only: bool | None = None) -> list[StockItem]:
    _require_read(owner, "list inventory items")
    organization = _active_organization(owner)
    return owner._item_repo.list_for_organization(organization.id, active_only=active_only)


def search_items(
    owner: Any,
    *,
    search_text: str = "",
    active_only: bool | None = True,
    category_code: str | None = None,
    equipment_only: bool | None = None,
    project_usage_only: bool | None = None,
    maintenance_usage_only: bool | None = None,
) -> list[StockItem]:
    _require_read(owner, "search inventory items")
    normalized_search = normalize_optional_text(search_text).lower()
    normalized_category_code = normalize_optional_text(category_code).upper()
    rows = list_items(owner, active_only=active_only)
    category_lookup = _category_lookup(owner)
    if not normalized_search:
        filtered = rows
    else:
        filtered = [
            item
            for item in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        item.item_code,
                        item.name,
                        item.description,
                        item.item_type,
                        item.category_code,
                        item.commodity_code,
                        item.status,
                        item.stock_uom,
                        _category_label(item, category_lookup),
                    ],
                )
            ).lower()
        ]
    result: list[StockItem] = []
    for item in filtered:
        category = category_lookup.get(item.category_code)
        if normalized_category_code and item.category_code != normalized_category_code:
            continue
        if equipment_only is True and not _is_equipment_item(item, category):
            continue
        if equipment_only is False and _is_equipment_item(item, category):
            continue
        if project_usage_only is True and not bool(category and category.supports_project_usage):
            continue
        if project_usage_only is False and bool(category and category.supports_project_usage):
            continue
        if maintenance_usage_only is True and not bool(category and category.supports_maintenance_usage):
            continue
        if maintenance_usage_only is False and bool(category and category.supports_maintenance_usage):
            continue
        result.append(item)
    return result


def get_item(owner: Any, item_id: str) -> StockItem:
    _require_read(owner, "view inventory item")
    return get_item_for_internal_use(owner, item_id)


def get_item_for_internal_use(owner: Any, item_id: str) -> StockItem:
    organization = _active_organization(owner)
    item = owner._item_repo.get(item_id)
    if item is None or item.organization_id != organization.id:
        raise NotFoundError(
            "Inventory item not found in the active organization.",
            code="INVENTORY_ITEM_NOT_FOUND",
        )
    return item


def find_item_by_code(owner: Any, item_code: str) -> StockItem | None:
    _require_read(owner, "resolve inventory item")
    organization = _active_organization(owner)
    normalized_code = normalize_inventory_code(item_code, label="Item code")
    return owner._item_repo.get_by_code(organization.id, normalized_code)


def _category_lookup(owner: Any) -> dict[str, InventoryItemCategory]:
    if owner._category_repo is None:
        return {}
    organization = _active_organization(owner)
    return {
        category.category_code: category
        for category in owner._category_repo.list_for_organization(
            organization.id,
            active_only=None,
        )
    }


def _category_label(
    item: StockItem,
    category_lookup: dict[str, InventoryItemCategory],
) -> str:
    category = category_lookup.get(item.category_code)
    if category is None:
        return item.category_code
    return f"{category.category_code} {category.name} {category.category_type}"


def _is_equipment_item(
    item: StockItem,
    category: InventoryItemCategory | None,
) -> bool:
    if category is not None:
        return category.is_equipment
    return normalize_optional_text(item.item_type).upper() == "EQUIPMENT"


__all__ = [
    "_category_label",
    "_category_lookup",
    "_is_equipment_item",
    "find_item_by_code",
    "get_item",
    "get_item_for_internal_use",
    "list_items",
    "search_items",
]
