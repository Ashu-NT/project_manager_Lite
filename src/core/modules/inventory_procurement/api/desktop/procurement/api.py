from __future__ import annotations

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.inventory import InventoryService
from src.core.modules.inventory_procurement.application.procurement import (
    ProcurementService,
    PurchasingService,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_enum_label,
)
from src.core.modules.inventory_procurement.api.desktop.procurement.purchase_orders import (
    InventoryPurchaseOrderCreateCommand,
    InventoryPurchaseOrderDesktopDto,
    InventoryPurchaseOrderLineCreateCommand,
    InventoryPurchaseOrderLineDesktopDto,
    InventoryPurchaseOrderUpdateCommand,
    serialize_purchase_order,
    serialize_purchase_order_line,
)
from src.core.modules.inventory_procurement.api.desktop.procurement.receipts import (
    InventoryReceiptDesktopDto,
    InventoryReceiptLineDesktopDto,
    InventoryReceiptPostCommand,
    serialize_receipt,
    serialize_receipt_line,
)
from src.core.modules.inventory_procurement.api.desktop.procurement.requisitions import (
    InventoryRequisitionCreateCommand,
    InventoryRequisitionDesktopDto,
    InventoryRequisitionLineCreateCommand,
    InventoryRequisitionLineDesktopDto,
    InventoryRequisitionUpdateCommand,
    serialize_requisition,
    serialize_requisition_line,
)
from src.core.modules.inventory_procurement.api.desktop.procurement.statuses import (
    InventoryProcurementStatusDescriptor,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryBusinessPartyOptionDescriptor,
    InventoryCatalogItemOptionDescriptor,
    InventorySiteOptionDescriptor,
    InventoryStoreroomOptionDescriptor,
    serialize_business_party_option,
    serialize_item_option,
    serialize_site_option,
    serialize_storeroom_option,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderStatus,
    PurchaseRequisitionStatus,
)


class InventoryProcurementProcurementDesktopApi:
    def __init__(
        self,
        *,
        procurement_service: ProcurementService | None = None,
        purchasing_service: PurchasingService | None = None,
        reference_service: InventoryReferenceService | None = None,
        inventory_service: InventoryService | None = None,
        item_service: ItemMasterService | None = None,
    ) -> None:
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._reference_service = reference_service
        self._inventory_service = inventory_service
        self._item_service = item_service

    def list_requisition_statuses(self) -> tuple[InventoryProcurementStatusDescriptor, ...]:
        return tuple(
            InventoryProcurementStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in PurchaseRequisitionStatus
        )

    def list_purchase_order_statuses(self) -> tuple[InventoryProcurementStatusDescriptor, ...]:
        return tuple(
            InventoryProcurementStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in PurchaseOrderStatus
        )

    def list_site_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventorySiteOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        sites = sorted(
            self._reference_service.list_sites(active_only=active_only),
            key=lambda row: str(getattr(row, "site_code", "") or "").casefold(),
        )
        return tuple(serialize_site_option(row) for row in sites)

    def list_supplier_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryBusinessPartyOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        parties = sorted(
            self._reference_service.list_business_parties(active_only=active_only),
            key=lambda row: str(getattr(row, "party_code", "") or "").casefold(),
        )
        return tuple(serialize_business_party_option(row) for row in parties)

    def list_item_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryCatalogItemOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        items = sorted(
            self._item_service.list_items(active_only=active_only),
            key=lambda row: str(getattr(row, "item_code", "") or "").casefold(),
        )
        return tuple(serialize_item_option(row) for row in items)

    def list_storeroom_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        storerooms = self._inventory_service.list_storerooms(
            active_only=active_only,
            site_id=site_id,
        )
        ordered = sorted(
            storerooms,
            key=lambda row: str(getattr(row, "storeroom_code", "") or "").casefold(),
        )
        return tuple(
            serialize_storeroom_option(row, site_lookup=site_lookup)
            for row in ordered
        )

    def list_requisitions(
        self,
        *,
        status: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryRequisitionDesktopDto, ...]:
        if self._procurement_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        storeroom_lookup = {
            row.value: row.label for row in self.list_storeroom_options(active_only=None)
        }
        rows = sorted(
            self._procurement_service.list_requisitions(status=status, limit=limit),
            key=lambda row: str(getattr(row, "requisition_number", "") or "").casefold(),
        )
        requisition_lookup = {
            row.id: clean_text(getattr(row, "requisition_number", ""))
            for row in rows
        }
        return tuple(
            serialize_requisition(
                row,
                site_lookup=site_lookup,
                storeroom_lookup=storeroom_lookup,
                requisition_lookup=requisition_lookup,
            )
            for row in rows
        )

    def list_requisition_lines(
        self,
        requisition_id: str,
    ) -> tuple[InventoryRequisitionLineDesktopDto, ...]:
        if self._procurement_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_item_options(active_only=None)}
        supplier_lookup = {
            row.value: row.label for row in self.list_supplier_options(active_only=None)
        }
        rows = sorted(
            self._procurement_service.list_requisition_lines(requisition_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            serialize_requisition_line(
                row,
                item_lookup=item_lookup,
                supplier_lookup=supplier_lookup,
            )
            for row in rows
        )

    def list_purchase_orders(
        self,
        *,
        status: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryPurchaseOrderDesktopDto, ...]:
        if self._purchasing_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        supplier_lookup = {
            row.value: row.label for row in self.list_supplier_options(active_only=None)
        }
        requisition_lookup = {
            row.id: clean_text(getattr(row, "requisition_number", ""))
            for row in self.list_requisitions(status=None, limit=500)
        }
        rows = sorted(
            self._purchasing_service.list_purchase_orders(status=status, limit=limit),
            key=lambda row: str(getattr(row, "po_number", "") or "").casefold(),
        )
        return tuple(
            serialize_purchase_order(
                row,
                site_lookup=site_lookup,
                supplier_lookup=supplier_lookup,
                requisition_lookup=requisition_lookup,
            )
            for row in rows
        )

    def list_purchase_order_lines(
        self,
        purchase_order_id: str,
    ) -> tuple[InventoryPurchaseOrderLineDesktopDto, ...]:
        if self._purchasing_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_item_options(active_only=None)}
        storeroom_lookup = {
            row.value: row.label for row in self.list_storeroom_options(active_only=None)
        }
        rows = sorted(
            self._purchasing_service.list_purchase_order_lines(purchase_order_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            serialize_purchase_order_line(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def list_receipts(
        self,
        *,
        purchase_order_id: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryReceiptDesktopDto, ...]:
        if self._purchasing_service is None:
            return ()
        purchase_order_lookup = {
            row.id: clean_text(getattr(row, "po_number", ""))
            for row in self.list_purchase_orders(status=None, limit=500)
        }
        site_lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        supplier_lookup = {
            row.value: row.label for row in self.list_supplier_options(active_only=None)
        }
        rows = sorted(
            self._purchasing_service.list_receipts(
                purchase_order_id=purchase_order_id,
                limit=limit,
            ),
            key=lambda row: str(getattr(row, "receipt_number", "") or "").casefold(),
            reverse=True,
        )
        return tuple(
            serialize_receipt(
                row,
                purchase_order_lookup=purchase_order_lookup,
                site_lookup=site_lookup,
                supplier_lookup=supplier_lookup,
            )
            for row in rows
        )

    def list_receipt_lines(
        self,
        receipt_id: str,
    ) -> tuple[InventoryReceiptLineDesktopDto, ...]:
        if self._purchasing_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_item_options(active_only=None)}
        storeroom_lookup = {
            row.value: row.label for row in self.list_storeroom_options(active_only=None)
        }
        rows = sorted(
            self._purchasing_service.list_receipt_lines(receipt_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            serialize_receipt_line(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in rows
        )

    def create_requisition(
        self,
        command: InventoryRequisitionCreateCommand,
    ) -> InventoryRequisitionDesktopDto:
        requisition = self._require_procurement_service().create_requisition(
            requesting_site_id=command.requesting_site_id,
            requesting_storeroom_id=command.requesting_storeroom_id,
            purpose=command.purpose,
            needed_by_date=command.needed_by_date,
            priority=command.priority,
            source_reference_type=command.source_reference_type,
            source_reference_id=command.source_reference_id,
            source_module=command.source_module,
            source_entity_type=command.source_entity_type,
            source_code_snapshot=command.source_code_snapshot,
            source_title_snapshot=command.source_title_snapshot,
            source_status_snapshot=command.source_status_snapshot,
            notes=command.notes,
            requisition_number=command.requisition_number,
        )
        return self._serialize_requisition(requisition)

    def update_requisition(
        self,
        command: InventoryRequisitionUpdateCommand,
    ) -> InventoryRequisitionDesktopDto:
        requisition = self._require_procurement_service().update_requisition(
            command.requisition_id,
            requesting_site_id=command.requesting_site_id,
            requesting_storeroom_id=command.requesting_storeroom_id,
            purpose=command.purpose,
            needed_by_date=command.needed_by_date,
            priority=command.priority,
            source_reference_type=command.source_reference_type,
            source_reference_id=command.source_reference_id,
            source_module=command.source_module,
            source_entity_type=command.source_entity_type,
            source_code_snapshot=command.source_code_snapshot,
            source_title_snapshot=command.source_title_snapshot,
            source_status_snapshot=command.source_status_snapshot,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_requisition(requisition)

    def add_requisition_line(
        self,
        command: InventoryRequisitionLineCreateCommand,
    ) -> InventoryRequisitionLineDesktopDto:
        line = self._require_procurement_service().add_requisition_line(
            command.requisition_id,
            stock_item_id=command.stock_item_id,
            quantity_requested=command.quantity_requested,
            uom=command.uom,
            description=command.description,
            needed_by_date=command.needed_by_date,
            estimated_unit_cost=command.estimated_unit_cost,
            suggested_supplier_party_id=command.suggested_supplier_party_id,
            notes=command.notes,
        )
        return self._serialize_requisition_line(line)

    def submit_requisition(
        self,
        requisition_id: str,
        *,
        note: str = "",
    ) -> InventoryRequisitionDesktopDto:
        requisition = self._require_procurement_service().submit_requisition(
            requisition_id,
            note=note,
        )
        return self._serialize_requisition(requisition)

    def cancel_requisition(
        self,
        requisition_id: str,
        *,
        note: str = "",
        expected_version: int | None = None,
    ) -> InventoryRequisitionDesktopDto:
        requisition = self._require_procurement_service().cancel_requisition(
            requisition_id,
            note=note,
            expected_version=expected_version,
        )
        return self._serialize_requisition(requisition)

    def create_purchase_order(
        self,
        command: InventoryPurchaseOrderCreateCommand,
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().create_purchase_order(
            site_id=command.site_id,
            supplier_party_id=command.supplier_party_id,
            currency_code=command.currency_code,
            source_requisition_id=command.source_requisition_id,
            order_date=command.order_date,
            expected_delivery_date=command.expected_delivery_date,
            supplier_reference=command.supplier_reference,
            notes=command.notes,
            po_number=command.po_number,
        )
        return self._serialize_purchase_order(purchase_order)

    def update_purchase_order(
        self,
        command: InventoryPurchaseOrderUpdateCommand,
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().update_purchase_order(
            command.purchase_order_id,
            site_id=command.site_id,
            supplier_party_id=command.supplier_party_id,
            currency_code=command.currency_code,
            source_requisition_id=command.source_requisition_id,
            expected_delivery_date=command.expected_delivery_date,
            supplier_reference=command.supplier_reference,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_purchase_order(purchase_order)

    def add_purchase_order_line(
        self,
        command: InventoryPurchaseOrderLineCreateCommand,
    ) -> InventoryPurchaseOrderLineDesktopDto:
        line = self._require_purchasing_service().add_purchase_order_line(
            command.purchase_order_id,
            stock_item_id=command.stock_item_id,
            destination_storeroom_id=command.destination_storeroom_id,
            quantity_ordered=command.quantity_ordered,
            uom=command.uom,
            unit_price=command.unit_price,
            expected_delivery_date=command.expected_delivery_date,
            description=command.description,
            source_requisition_line_id=command.source_requisition_line_id,
            notes=command.notes,
        )
        return self._serialize_purchase_order_line(line)

    def submit_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().submit_purchase_order(
            purchase_order_id,
            note=note,
        )
        return self._serialize_purchase_order(purchase_order)

    def send_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().send_purchase_order(
            purchase_order_id,
            note=note,
        )
        return self._serialize_purchase_order(purchase_order)

    def cancel_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
        expected_version: int | None = None,
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().cancel_purchase_order(
            purchase_order_id,
            note=note,
            expected_version=expected_version,
        )
        return self._serialize_purchase_order(purchase_order)

    def close_purchase_order(
        self,
        purchase_order_id: str,
        *,
        note: str = "",
    ) -> InventoryPurchaseOrderDesktopDto:
        purchase_order = self._require_purchasing_service().close_purchase_order(
            purchase_order_id,
            note=note,
        )
        return self._serialize_purchase_order(purchase_order)

    def post_receipt(
        self,
        command: InventoryReceiptPostCommand,
    ) -> InventoryReceiptDesktopDto:
        receipt = self._require_purchasing_service().post_receipt(
            command.purchase_order_id,
            receipt_lines=[
                {
                    "purchase_order_line_id": line.purchase_order_line_id,
                    "quantity_accepted": line.quantity_accepted,
                    "quantity_rejected": line.quantity_rejected,
                    "unit_cost": line.unit_cost,
                    "lot_number": line.lot_number,
                    "serial_number": line.serial_number,
                    "expiry_date": line.expiry_date,
                    "notes": line.notes,
                }
                for line in command.receipt_lines
            ],
            receipt_date=command.receipt_date,
            supplier_delivery_reference=command.supplier_delivery_reference,
            notes=command.notes,
            receipt_number=command.receipt_number,
        )
        return self._serialize_receipt(receipt)

    def _serialize_requisition(self, row) -> InventoryRequisitionDesktopDto:
        site_lookup = {entry.value: entry.label for entry in self.list_site_options(active_only=None)}
        storeroom_lookup = {
            entry.value: entry.label for entry in self.list_storeroom_options(active_only=None)
        }
        return serialize_requisition(
            row,
            site_lookup=site_lookup,
            storeroom_lookup=storeroom_lookup,
            requisition_lookup={row.id: clean_text(getattr(row, "requisition_number", ""))},
        )

    def _serialize_requisition_line(self, row) -> InventoryRequisitionLineDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_item_options(active_only=None)}
        supplier_lookup = {
            entry.value: entry.label for entry in self.list_supplier_options(active_only=None)
        }
        return serialize_requisition_line(
            row,
            item_lookup=item_lookup,
            supplier_lookup=supplier_lookup,
        )

    def _serialize_purchase_order(self, row) -> InventoryPurchaseOrderDesktopDto:
        site_lookup = {entry.value: entry.label for entry in self.list_site_options(active_only=None)}
        supplier_lookup = {
            entry.value: entry.label for entry in self.list_supplier_options(active_only=None)
        }
        requisition_lookup = {
            entry.id: clean_text(getattr(entry, "requisition_number", ""))
            for entry in self.list_requisitions(status=None, limit=500)
        }
        return serialize_purchase_order(
            row,
            site_lookup=site_lookup,
            supplier_lookup=supplier_lookup,
            requisition_lookup=requisition_lookup,
        )

    def _serialize_purchase_order_line(self, row) -> InventoryPurchaseOrderLineDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_item_options(active_only=None)}
        storeroom_lookup = {
            entry.value: entry.label for entry in self.list_storeroom_options(active_only=None)
        }
        return serialize_purchase_order_line(
            row,
            item_lookup=item_lookup,
            storeroom_lookup=storeroom_lookup,
        )

    def _serialize_receipt(self, row) -> InventoryReceiptDesktopDto:
        purchase_order_lookup = {
            entry.id: clean_text(getattr(entry, "po_number", ""))
            for entry in self.list_purchase_orders(status=None, limit=500)
        }
        site_lookup = {entry.value: entry.label for entry in self.list_site_options(active_only=None)}
        supplier_lookup = {
            entry.value: entry.label for entry in self.list_supplier_options(active_only=None)
        }
        return serialize_receipt(
            row,
            purchase_order_lookup=purchase_order_lookup,
            site_lookup=site_lookup,
            supplier_lookup=supplier_lookup,
        )

    def _require_procurement_service(self) -> ProcurementService:
        if self._procurement_service is None:
            raise RuntimeError("Inventory requisition desktop API is not connected.")
        return self._procurement_service

    def _require_purchasing_service(self) -> PurchasingService:
        if self._purchasing_service is None:
            raise RuntimeError("Inventory purchasing desktop API is not connected.")
        return self._purchasing_service


def build_inventory_procurement_procurement_desktop_api(
    *,
    procurement_service: ProcurementService | None = None,
    purchasing_service: PurchasingService | None = None,
    reference_service: InventoryReferenceService | None = None,
    inventory_service: InventoryService | None = None,
    item_service: ItemMasterService | None = None,
) -> InventoryProcurementProcurementDesktopApi:
    return InventoryProcurementProcurementDesktopApi(
        procurement_service=procurement_service,
        purchasing_service=purchasing_service,
        reference_service=reference_service,
        inventory_service=inventory_service,
        item_service=item_service,
    )


__all__ = [
    "InventoryProcurementProcurementDesktopApi",
    "build_inventory_procurement_procurement_desktop_api",
]
