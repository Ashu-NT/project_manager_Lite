from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.common.support import (
    normalize_optional_text,
)
from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
    StockItem,
)
from src.core.platform.audit.helpers import record_audit


def _build_category_create_audit_details(
    organization_id: str,
    category: InventoryItemCategory,
) -> dict[str, object]:
    return {
        "organization_id": organization_id,
        "category_code": category.category_code,
        "category_type": category.category_type,
        "is_equipment": category.is_equipment,
        "supports_project_usage": category.supports_project_usage,
        "supports_maintenance_usage": category.supports_maintenance_usage,
    }


def _build_category_update_audit_details(
    organization_id: str,
    category: InventoryItemCategory,
) -> dict[str, object]:
    details = _build_category_create_audit_details(organization_id, category)
    details["is_active"] = category.is_active
    return details


def _build_item_audit_details(
    organization_id: str,
    item: StockItem,
) -> dict[str, object]:
    return {
        "organization_id": organization_id,
        "item_code": item.item_code,
        "name": item.name,
        "status": item.status,
        "stock_uom": item.stock_uom,
        "preferred_party_id": item.preferred_party_id or "",
    }


def _build_document_audit_details(
    document_id: str,
    link_role: str,
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "link_role": normalize_optional_text(link_role) or "reference",
    }


def record_inventory_item_category_create_audit(
    owner: Any,
    *,
    organization_id: str,
    category: InventoryItemCategory,
) -> None:
    record_audit(
        owner,
        action="inventory_item_category.create",
        entity_type="inventory_item_category",
        entity_id=category.id,
        details=_build_category_create_audit_details(organization_id, category),
    )


def record_inventory_item_category_update_audit(
    owner: Any,
    *,
    organization_id: str,
    category: InventoryItemCategory,
) -> None:
    record_audit(
        owner,
        action="inventory_item_category.update",
        entity_type="inventory_item_category",
        entity_id=category.id,
        details=_build_category_update_audit_details(organization_id, category),
    )


def record_inventory_item_create_audit(
    owner: Any,
    *,
    organization_id: str,
    item: StockItem,
) -> None:
    record_audit(
        owner,
        action="inventory_item.create",
        entity_type="inventory_item",
        entity_id=item.id,
        details=_build_item_audit_details(organization_id, item),
    )


def record_inventory_item_update_audit(
    owner: Any,
    *,
    organization_id: str,
    item: StockItem,
) -> None:
    record_audit(
        owner,
        action="inventory_item.update",
        entity_type="inventory_item",
        entity_id=item.id,
        details=_build_item_audit_details(organization_id, item),
    )


def record_inventory_item_link_document_audit(
    owner: Any,
    *,
    item_id: str,
    document_id: str,
    link_role: str,
) -> None:
    record_audit(
        owner,
        action="inventory_item.link_document",
        entity_type="inventory_item",
        entity_id=item_id,
        details=_build_document_audit_details(document_id, link_role),
    )


def record_inventory_item_unlink_document_audit(
    owner: Any,
    *,
    item_id: str,
    document_id: str,
    link_role: str,
) -> None:
    record_audit(
        owner,
        action="inventory_item.unlink_document",
        entity_type="inventory_item",
        entity_id=item_id,
        details=_build_document_audit_details(document_id, link_role),
    )


__all__ = [
    "record_inventory_item_category_create_audit",
    "record_inventory_item_category_update_audit",
    "record_inventory_item_create_audit",
    "record_inventory_item_link_document_audit",
    "record_inventory_item_unlink_document_audit",
    "record_inventory_item_update_audit",
]
