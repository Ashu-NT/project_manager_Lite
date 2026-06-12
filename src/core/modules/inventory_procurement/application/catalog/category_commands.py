from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.catalog.catalog_access import (
    _require_manage,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_audit import (
    record_inventory_item_category_create_audit,
    record_inventory_item_category_update_audit,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.common.support import (
    normalize_inventory_code,
    normalize_inventory_name,
    normalize_item_category_type,
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events


def create_category(
    owner: Any,
    *,
    category_code: str,
    name: str,
    description: str = "",
    category_type: str = "MATERIAL",
    is_equipment: bool = False,
    supports_project_usage: bool = False,
    supports_maintenance_usage: bool = False,
    is_active: bool = True,
) -> InventoryItemCategory:
    _require_manage(owner, "create inventory item category")
    organization = _active_organization(owner)
    normalized_code = normalize_inventory_code(category_code, label="Category code")
    if owner._category_repo.get_by_code(organization.id, normalized_code) is not None:
        raise ValidationError(
            "Category code already exists in the active organization.",
            code="INVENTORY_CATEGORY_CODE_EXISTS",
        )
    resolved_type = normalize_item_category_type(category_type)
    category = InventoryItemCategory.create(
        organization_id=organization.id,
        category_code=normalized_code,
        name=normalize_inventory_name(name, label="Category name"),
        description=normalize_optional_text(description),
        category_type=resolved_type,
        is_equipment=bool(is_equipment or resolved_type == "EQUIPMENT"),
        supports_project_usage=bool(supports_project_usage),
        supports_maintenance_usage=bool(supports_maintenance_usage),
        is_active=bool(is_active),
    )
    try:
        owner._category_repo.add(category)
        owner._session.commit()
    except IntegrityError as exc:
        owner._session.rollback()
        raise ValidationError(
            "Category code already exists in the active organization.",
            code="INVENTORY_CATEGORY_CODE_EXISTS",
        ) from exc
    except Exception:
        owner._session.rollback()
        raise
    record_inventory_item_category_create_audit(
        owner,
        organization_id=organization.id,
        category=category,
    )
    domain_events.inventory_item_categories_changed.emit(category.id)
    return category


def update_category(
    owner: Any,
    category_id: str,
    *,
    category_code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    category_type: str | None = None,
    is_equipment: bool | None = None,
    supports_project_usage: bool | None = None,
    supports_maintenance_usage: bool | None = None,
    is_active: bool | None = None,
    expected_version: int | None = None,
) -> InventoryItemCategory:
    _require_manage(owner, "update inventory item category")
    organization = _active_organization(owner)
    category = owner._category_repo.get(category_id)
    if category is None or category.organization_id != organization.id:
        raise NotFoundError(
            "Inventory item category not found in the active organization.",
            code="INVENTORY_CATEGORY_NOT_FOUND",
        )
    if expected_version is not None and category.version != expected_version:
        raise ConcurrencyError(
            "Inventory item category changed since you opened it. Refresh and try again.",
            code="STALE_WRITE",
        )
    if category_code is not None:
        normalized_code = normalize_inventory_code(category_code, label="Category code")
        existing = owner._category_repo.get_by_code(organization.id, normalized_code)
        if existing is not None and existing.id != category.id:
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            )
        category.category_code = normalized_code
    if name is not None:
        category.name = normalize_inventory_name(name, label="Category name")
    if description is not None:
        category.description = normalize_optional_text(description)
    next_type = category.category_type
    if category_type is not None:
        next_type = normalize_item_category_type(category_type)
        category.category_type = next_type
    next_is_equipment = category.is_equipment if is_equipment is None else bool(is_equipment)
    if next_type == "EQUIPMENT":
        next_is_equipment = True
    category.is_equipment = next_is_equipment
    if supports_project_usage is not None:
        category.supports_project_usage = bool(supports_project_usage)
    if supports_maintenance_usage is not None:
        category.supports_maintenance_usage = bool(supports_maintenance_usage)
    if is_active is not None:
        category.is_active = bool(is_active)
    category.updated_at = datetime.now(timezone.utc)
    try:
        owner._category_repo.update(category)
        owner._session.commit()
    except IntegrityError as exc:
        owner._session.rollback()
        raise ValidationError(
            "Category code already exists in the active organization.",
            code="INVENTORY_CATEGORY_CODE_EXISTS",
        ) from exc
    except Exception:
        owner._session.rollback()
        raise
    record_inventory_item_category_update_audit(
        owner,
        organization_id=organization.id,
        category=category,
    )
    domain_events.inventory_item_categories_changed.emit(category.id)
    return category


__all__ = ["create_category", "update_category"]
