from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.catalog.models import (
    InventoryDocumentOptionDescriptor,
    InventoryItemCreateCommand,
    InventoryItemDesktopDto,
    InventoryItemUpdateCommand,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.serializers import (
    serialize_document,
    serialize_item,
)


class InventoryCatalogDesktopItemMixin:
    def list_items(
        self,
        *,
        active_only: bool | None = None,
        search_text: str = "",
        category_code: str | None = None,
        equipment_only: bool | None = None,
        project_usage_only: bool | None = None,
        maintenance_usage_only: bool | None = None,
    ) -> tuple[InventoryItemDesktopDto, ...]:
        if self._item_service is None:
            return ()
        category_lookup = {
            row.category_code: row.name for row in self.list_categories(active_only=None)
        }
        party_lookup = {
            row.value: row.label
            for row in self.list_business_parties(active_only=None)
        }
        if (
            search_text
            or category_code
            or equipment_only is not None
            or project_usage_only is not None
            or maintenance_usage_only is not None
        ):
            items = self._item_service.search_items(
                search_text=search_text,
                active_only=active_only,
                category_code=category_code,
                equipment_only=equipment_only,
                project_usage_only=project_usage_only,
                maintenance_usage_only=maintenance_usage_only,
            )
        else:
            items = self._item_service.list_items(active_only=active_only)
        ordered = sorted(
            items,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "item_code", "") or "").casefold(),
            ),
        )
        return tuple(
            serialize_item(
                row,
                category_lookup=category_lookup,
                party_lookup=party_lookup,
            )
            for row in ordered
        )

    def list_available_documents(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        documents = sorted(
            self._item_service.list_available_documents(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "document_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_document(row) for row in documents)

    def list_linked_documents(
        self,
        item_id: str,
        *,
        active_only: bool | None = None,
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        documents = sorted(
            self._item_service.list_linked_documents(item_id, active_only=active_only),
            key=lambda row: str(getattr(row, "document_code", "") or "").casefold(),
        )
        return tuple(serialize_document(row) for row in documents)

    def create_item(self, command: InventoryItemCreateCommand) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.create_item(
            item_code=command.item_code,
            name=command.name,
            description=command.description,
            item_type=command.item_type,
            status=command.status,
            stock_uom=command.stock_uom,
            order_uom=command.order_uom,
            issue_uom=command.issue_uom,
            order_uom_ratio=command.order_uom_ratio,
            issue_uom_ratio=command.issue_uom_ratio,
            category_code=command.category_code,
            commodity_code=command.commodity_code,
            is_stocked=command.is_stocked,
            is_purchase_allowed=command.is_purchase_allowed,
            default_reorder_policy=command.default_reorder_policy,
            min_qty=command.min_qty,
            max_qty=command.max_qty,
            reorder_point=command.reorder_point,
            reorder_qty=command.reorder_qty,
            lead_time_days=command.lead_time_days,
            is_lot_tracked=command.is_lot_tracked,
            is_serial_tracked=command.is_serial_tracked,
            shelf_life_days=command.shelf_life_days,
            preferred_party_id=command.preferred_party_id,
            notes=command.notes,
        )
        return self._serialize_item(item)

    def update_item(self, command: InventoryItemUpdateCommand) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.update_item(
            command.item_id,
            item_code=command.item_code,
            name=command.name,
            description=command.description,
            item_type=command.item_type,
            status=command.status,
            stock_uom=command.stock_uom,
            order_uom=command.order_uom,
            issue_uom=command.issue_uom,
            order_uom_ratio=command.order_uom_ratio,
            issue_uom_ratio=command.issue_uom_ratio,
            category_code=command.category_code,
            commodity_code=command.commodity_code,
            is_stocked=command.is_stocked,
            is_purchase_allowed=command.is_purchase_allowed,
            default_reorder_policy=command.default_reorder_policy,
            min_qty=command.min_qty,
            max_qty=command.max_qty,
            reorder_point=command.reorder_point,
            reorder_qty=command.reorder_qty,
            lead_time_days=command.lead_time_days,
            is_lot_tracked=command.is_lot_tracked,
            is_serial_tracked=command.is_serial_tracked,
            shelf_life_days=command.shelf_life_days,
            preferred_party_id=command.preferred_party_id,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_item(item)

    def change_item_status(
        self,
        item_id: str,
        *,
        status: str,
        expected_version: int | None = None,
    ) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.update_item(
            item_id,
            status=status,
            expected_version=expected_version,
        )
        return self._serialize_item(item)

    def toggle_item_active(
        self,
        item_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryItemDesktopDto:
        service = self._require_item_service()
        item = service.get_item(item_id)
        updated = service.update_item(
            item_id,
            is_active=not bool(getattr(item, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_item(updated)

    def link_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        service = self._require_item_service()
        service.link_document(item_id, document_id=document_id, link_role=link_role)
        return self.list_linked_documents(item_id, active_only=None)

    def unlink_document(
        self,
        item_id: str,
        *,
        document_id: str,
        link_role: str = "reference",
    ) -> tuple[InventoryDocumentOptionDescriptor, ...]:
        service = self._require_item_service()
        service.unlink_document(item_id, document_id=document_id, link_role=link_role)
        return self.list_linked_documents(item_id, active_only=None)

    def _serialize_item(self, item) -> InventoryItemDesktopDto:
        category_lookup = {
            row.category_code: row.name for row in self.list_categories(active_only=None)
        }
        party_lookup = {
            row.value: row.label
            for row in self.list_business_parties(active_only=None)
        }
        return serialize_item(
            item,
            category_lookup=category_lookup,
            party_lookup=party_lookup,
        )


__all__ = ["InventoryCatalogDesktopItemMixin"]
