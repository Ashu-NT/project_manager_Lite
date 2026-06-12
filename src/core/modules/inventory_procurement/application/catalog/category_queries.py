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
    normalize_item_category_type,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
)
from src.core.platform.common.exceptions import NotFoundError


def list_categories(
    owner: Any,
    *,
    active_only: bool | None = None,
    category_type: str | None = None,
) -> list[InventoryItemCategory]:
    _require_read(owner, "list inventory item categories")
    organization = _active_organization(owner)
    resolved_type = normalize_item_category_type(category_type) if category_type else None
    return owner._category_repo.list_for_organization(
        organization.id,
        active_only=active_only,
        category_type=resolved_type,
    )


def search_categories(
    owner: Any,
    *,
    search_text: str = "",
    active_only: bool | None = True,
    category_type: str | None = None,
    equipment_only: bool | None = None,
    project_usage_only: bool | None = None,
    maintenance_usage_only: bool | None = None,
) -> list[InventoryItemCategory]:
    normalized_search = normalize_optional_text(search_text).lower()
    rows = list_categories(owner, active_only=active_only, category_type=category_type)
    filtered: list[InventoryItemCategory] = []
    for category in rows:
        if equipment_only is True and not category.is_equipment:
            continue
        if equipment_only is False and category.is_equipment:
            continue
        if project_usage_only is True and not category.supports_project_usage:
            continue
        if project_usage_only is False and category.supports_project_usage:
            continue
        if maintenance_usage_only is True and not category.supports_maintenance_usage:
            continue
        if maintenance_usage_only is False and category.supports_maintenance_usage:
            continue
        if normalized_search:
            haystack = " ".join(
                filter(
                    None,
                    [
                        category.category_code,
                        category.name,
                        category.description,
                        category.category_type,
                    ],
                )
            ).lower()
            if normalized_search not in haystack:
                continue
        filtered.append(category)
    return filtered


def get_category(owner: Any, category_id: str) -> InventoryItemCategory:
    _require_read(owner, "view inventory item category")
    organization = _active_organization(owner)
    category = owner._category_repo.get(category_id)
    if category is None or category.organization_id != organization.id:
        raise NotFoundError(
            "Inventory item category not found in the active organization.",
            code="INVENTORY_CATEGORY_NOT_FOUND",
        )
    return category


def find_category_by_code(
    owner: Any,
    category_code: str,
    *,
    active_only: bool | None = None,
) -> InventoryItemCategory | None:
    _require_read(owner, "resolve inventory item category")
    organization = _active_organization(owner)
    normalized_code = normalize_inventory_code(category_code, label="Category code")
    category = owner._category_repo.get_by_code(organization.id, normalized_code)
    if category is None:
        return None
    if active_only is not None and category.is_active != bool(active_only):
        return None
    return category


def list_project_resource_categories(
    owner: Any,
    *,
    active_only: bool | None = True,
) -> list[InventoryItemCategory]:
    return search_categories(owner, active_only=active_only, project_usage_only=True)


def list_maintenance_categories(
    owner: Any,
    *,
    active_only: bool | None = True,
) -> list[InventoryItemCategory]:
    return search_categories(owner, active_only=active_only, maintenance_usage_only=True)


__all__ = [
    "find_category_by_code",
    "get_category",
    "list_categories",
    "list_maintenance_categories",
    "list_project_resource_categories",
    "search_categories",
]
