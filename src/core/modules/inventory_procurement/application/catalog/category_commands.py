from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.core.modules.inventory_procurement.application.catalog.catalog_access import (
    _require_manage,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_activity import (
    record_inventory_item_category_create_activity,
    record_inventory_item_category_update_activity,
)
from src.core.modules.inventory_procurement.application.catalog.catalog_context import (
    _active_organization,
)
from src.core.modules.inventory_procurement.application.common.support import (
    normalize_inventory_code,
)
from src.core.modules.inventory_procurement.domain.catalog.catalog_events import (
    InventoryItemCategoryCreated,
    InventoryItemCategoryProfileUpdated,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.audit import record_audit_entry


def create_category(
    owner: Any,
    *,
    category_code: str,
    name: str,
    description: str = "",
    category_type: str = "MATERIAL",
    is_equipment: bool = False,
    supports_project_usage: bool = False,
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
    category = InventoryItemCategory.create(
        organization_id=organization.id,
        category_code=normalized_code,
        name=name,
        description=description,
        category_type=category_type,
        is_equipment=bool(is_equipment),
        supports_project_usage=bool(supports_project_usage),
        is_active=bool(is_active),
    )
    now = datetime.now(timezone.utc)
    uow = owner._require_uow_factory().create(context=owner._new_context())
    with uow:
        try:
            uow.categories.add(category)
        except IntegrityError as exc:
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            ) from exc
        record_inventory_item_category_create_activity(
            uow,
            organization_id=organization.id,
            category=category,
            commit=False,
        )
        record_audit_entry(
            uow,
            operation="create",
            entity_type="inventory_item_category",
            entity_id=category.id,
            module="inventory_procurement",
            organization_id=organization.id,
            severity="low",
            metadata={
                "category_code": category.category_code,
                "name": category.name,
                "category_type": category.category_type,
            },
            commit=False,
            fail_closed=True,
        )
        uow.record_event(
            InventoryItemCategoryCreated(
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                category_id=category.id,
                occurred_at=now,
            )
        )
        uow.commit()
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
    next_category_code = category.category_code
    if category_code is not None:
        next_category_code = normalize_inventory_code(category_code, label="Category code")
        existing = owner._category_repo.get_by_code(organization.id, next_category_code)
        if existing is not None and existing.id != category.id:
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            )
    candidate = replace(
        category,
        category_code=next_category_code,
        name=category.name if name is None else name,
        description=category.description if description is None else description,
        category_type=category.category_type if category_type is None else category_type,
        is_equipment=category.is_equipment if is_equipment is None else bool(is_equipment),
        supports_project_usage=(
            category.supports_project_usage
            if supports_project_usage is None
            else bool(supports_project_usage)
        ),
        is_active=category.is_active if is_active is None else bool(is_active),
    )
    if candidate == category:
        # True no-op (P24 §7): zero repository write, zero audit, zero typed event, no
        # synthetic version/updated_at bump.
        return category
    now = datetime.now(timezone.utc)
    candidate = replace(candidate, updated_at=now)
    uow = owner._require_uow_factory().create(context=owner._new_context())
    with uow:
        try:
            uow.categories.update(candidate)
        except IntegrityError as exc:
            raise ValidationError(
                "Category code already exists in the active organization.",
                code="INVENTORY_CATEGORY_CODE_EXISTS",
            ) from exc
        record_inventory_item_category_update_activity(
            uow,
            organization_id=organization.id,
            category=candidate,
            commit=False,
        )
        record_audit_entry(
            uow,
            operation="update",
            entity_type="inventory_item_category",
            entity_id=candidate.id,
            module="inventory_procurement",
            organization_id=organization.id,
            severity="low",
            metadata={
                "category_code": candidate.category_code,
                "name": candidate.name,
                "is_active": candidate.is_active,
            },
            commit=False,
            fail_closed=True,
        )
        uow.record_event(
            InventoryItemCategoryProfileUpdated(
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                category_id=candidate.id,
                occurred_at=now,
            )
        )
        uow.commit()
    return candidate


__all__ = ["create_category", "update_category"]
