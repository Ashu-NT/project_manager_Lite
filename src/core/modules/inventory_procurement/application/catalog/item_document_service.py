from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.application.catalog.catalog_audit import (
    record_inventory_item_link_document_audit,
    record_inventory_item_unlink_document_audit,
)
from src.core.modules.inventory_procurement.application.catalog.item_queries import (
    get_item,
)
from src.core.platform.documents import Document, DocumentLink
from src.core.shared.events.domain_events import domain_events


def list_linked_documents(
    owner: Any,
    item_id: str,
    *,
    active_only: bool | None = None,
) -> list[Document]:
    item = get_item(owner, item_id)
    return owner._document_integration_service.list_documents_for_entity(
        required_permission="inventory.read",
        operation_label="list inventory item documents",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=item.id,
        active_only=active_only,
    )


def list_available_documents(
    owner: Any,
    *,
    active_only: bool | None = True,
) -> list[Document]:
    return owner._document_integration_service.list_available_documents(
        required_permission="inventory.read",
        operation_label="list inventory document library",
        active_only=active_only,
    )


def link_document(
    owner: Any,
    item_id: str,
    *,
    document_id: str,
    link_role: str = "reference",
) -> DocumentLink:
    item = get_item(owner, item_id)
    link = owner._document_integration_service.link_existing_document(
        required_permission="inventory.manage",
        operation_label="link inventory item document",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=item.id,
        document_id=document_id,
        link_role=link_role,
    )
    record_inventory_item_link_document_audit(
        owner,
        item_id=item.id,
        document_id=document_id,
        link_role=link_role,
    )
    domain_events.inventory_items_changed.emit(item.id)
    return link


def unlink_document(
    owner: Any,
    item_id: str,
    *,
    document_id: str,
    link_role: str = "reference",
) -> None:
    item = get_item(owner, item_id)
    owner._document_integration_service.unlink_existing_document(
        required_permission="inventory.manage",
        operation_label="unlink inventory item document",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=item.id,
        document_id=document_id,
        link_role=link_role,
    )
    record_inventory_item_unlink_document_audit(
        owner,
        item_id=item.id,
        document_id=document_id,
        link_role=link_role,
    )
    domain_events.inventory_items_changed.emit(item.id)


__all__ = [
    "link_document",
    "list_available_documents",
    "list_linked_documents",
    "unlink_document",
]
