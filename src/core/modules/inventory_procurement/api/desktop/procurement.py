from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

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
    format_amount,
    format_date,
    format_datetime,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.catalog import (
    InventoryBusinessPartyOptionDescriptor,
    _serialize_business_party,
)
from src.core.modules.inventory_procurement.api.desktop.inventory import (
    InventoryCatalogItemOptionDescriptor,
    InventorySiteOptionDescriptor,
    InventoryStoreroomOptionDescriptor,
    _serialize_item_option,
    _serialize_site,
    _serialize_storeroom_option,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderStatus,
    PurchaseRequisitionStatus,
)


@dataclass(frozen=True)
class InventoryProcurementStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryRequisitionDesktopDto:
    id: str
    requisition_number: str
    requesting_site_id: str
    requesting_site_label: str
    requesting_storeroom_id: str
    requesting_storeroom_label: str
    requester_username: str
    status: str
    status_label: str
    purpose: str
    needed_by_date: date | None
    needed_by_date_label: str
    priority: str
    approval_request_id: str | None
    source_reference_type: str
    source_reference_id: str
    submitted_at_label: str
    approved_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryRequisitionLineDesktopDto:
    id: str
    purchase_requisition_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    description: str
    quantity_requested: float
    quantity_requested_label: str
    uom: str
    needed_by_date: date | None
    needed_by_date_label: str
    estimated_unit_cost: float
    estimated_unit_cost_label: str
    quantity_sourced: float
    quantity_sourced_label: str
    suggested_supplier_party_id: str | None
    suggested_supplier_label: str
    status: str
    status_label: str
    notes: str


@dataclass(frozen=True)
class InventoryPurchaseOrderDesktopDto:
    id: str
    po_number: str
    site_id: str
    site_label: str
    supplier_party_id: str
    supplier_label: str
    status: str
    status_label: str
    order_date: date | None
    order_date_label: str
    expected_delivery_date: date | None
    expected_delivery_date_label: str
    currency_code: str
    approval_request_id: str | None
    source_requisition_id: str | None
    source_requisition_label: str
    supplier_reference: str
    submitted_at_label: str
    approved_at_label: str
    sent_at_label: str
    closed_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryPurchaseOrderLineDesktopDto:
    id: str
    purchase_order_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    destination_storeroom_id: str
    destination_storeroom_label: str
    description: str
    quantity_ordered: float
    quantity_ordered_label: str
    quantity_received: float
    quantity_received_label: str
    quantity_rejected: float
    quantity_rejected_label: str
    uom: str
    unit_price: float
    unit_price_label: str
    expected_delivery_date: date | None
    expected_delivery_date_label: str
    source_requisition_line_id: str | None
    status: str
    status_label: str
    notes: str


@dataclass(frozen=True)
class InventoryReceiptDesktopDto:
    id: str
    receipt_number: str
    purchase_order_id: str
    purchase_order_label: str
    received_site_id: str
    received_site_label: str
    supplier_party_id: str
    supplier_label: str
    status: str
    status_label: str
    receipt_date_label: str
    supplier_delivery_reference: str
    received_by_username: str
    notes: str


@dataclass(frozen=True)
class InventoryReceiptLineDesktopDto:
    id: str
    receipt_header_id: str
    purchase_order_line_id: str
    line_number: int
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    quantity_accepted: float
    quantity_accepted_label: str
    quantity_rejected: float
    quantity_rejected_label: str
    uom: str
    unit_cost: float
    unit_cost_label: str
    lot_number: str
    serial_number: str
    expiry_date_label: str
    notes: str


@dataclass(frozen=True)
class InventoryRequisitionCreateCommand:
    requesting_site_id: str
    requesting_storeroom_id: str
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = "NORMAL"
    source_reference_type: str = ""
    source_reference_id: str = ""
    notes: str = ""
    requisition_number: str | None = None


@dataclass(frozen=True)
class InventoryRequisitionUpdateCommand:
    requisition_id: str
    requesting_site_id: str
    requesting_storeroom_id: str
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = "NORMAL"
    source_reference_type: str = ""
    source_reference_id: str = ""
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryRequisitionLineCreateCommand:
    requisition_id: str
    stock_item_id: str
    quantity_requested: float
    uom: str | None = None
    description: str = ""
    needed_by_date: date | None = None
    estimated_unit_cost: float = 0.0
    suggested_supplier_party_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryPurchaseOrderCreateCommand:
    site_id: str
    supplier_party_id: str
    currency_code: str | None = None
    source_requisition_id: str | None = None
    order_date: date | None = None
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""
    po_number: str | None = None


@dataclass(frozen=True)
class InventoryPurchaseOrderUpdateCommand:
    purchase_order_id: str
    site_id: str
    supplier_party_id: str
    currency_code: str | None = None
    source_requisition_id: str | None = None
    expected_delivery_date: date | None = None
    supplier_reference: str = ""
    notes: str = ""
    expected_version: int | None = None


@dataclass(frozen=True)
class InventoryPurchaseOrderLineCreateCommand:
    purchase_order_id: str
    stock_item_id: str
    destination_storeroom_id: str
    quantity_ordered: float
    uom: str | None = None
    unit_price: float = 0.0
    expected_delivery_date: date | None = None
    description: str = ""
    source_requisition_line_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryReceiptLineCommand:
    purchase_order_line_id: str
    quantity_accepted: float
    quantity_rejected: float = 0.0
    unit_cost: float | None = None
    lot_number: str = ""
    serial_number: str = ""
    expiry_date: date | None = None
    notes: str = ""


@dataclass(frozen=True)
class InventoryReceiptPostCommand:
    purchase_order_id: str
    receipt_lines: tuple[InventoryReceiptLineCommand, ...]
    receipt_date: datetime | None = None
    supplier_delivery_reference: str = ""
    notes: str = ""
    receipt_number: str | None = None


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
        return tuple(_serialize_site(row) for row in sites)

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
        return tuple(_serialize_business_party(row) for row in parties)

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
        return tuple(_serialize_item_option(row) for row in items)

    def list_storeroom_options(
        self,
        *,
        active_only: bool | None = True,
        site_id: str | None = None,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_site_options(active_only=None)}
        storerooms = self._inventory_service.list_storerooms(active_only=active_only, site_id=site_id)
        ordered = sorted(
            storerooms,
            key=lambda row: str(getattr(row, "storeroom_code", "") or "").casefold(),
        )
        return tuple(
            _serialize_storeroom_option(row, site_lookup=site_lookup)
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
        storeroom_lookup = {row.value: row.label for row in self.list_storeroom_options(active_only=None)}
        rows = sorted(
            self._procurement_service.list_requisitions(status=status, limit=limit),
            key=lambda row: str(getattr(row, "requisition_number", "") or "").casefold(),
        )
        requisition_lookup = {
            row.id: clean_text(getattr(row, "requisition_number", ""))
            for row in rows
        }
        return tuple(
            _serialize_requisition(
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
        supplier_lookup = {row.value: row.label for row in self.list_supplier_options(active_only=None)}
        rows = sorted(
            self._procurement_service.list_requisition_lines(requisition_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            _serialize_requisition_line(
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
        supplier_lookup = {row.value: row.label for row in self.list_supplier_options(active_only=None)}
        requisition_lookup = {
            row.id: clean_text(getattr(row, "requisition_number", ""))
            for row in self.list_requisitions(status=None, limit=500)
        }
        rows = sorted(
            self._purchasing_service.list_purchase_orders(status=status, limit=limit),
            key=lambda row: str(getattr(row, "po_number", "") or "").casefold(),
        )
        return tuple(
            _serialize_purchase_order(
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
        storeroom_lookup = {row.value: row.label for row in self.list_storeroom_options(active_only=None)}
        rows = sorted(
            self._purchasing_service.list_purchase_order_lines(purchase_order_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            _serialize_purchase_order_line(
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
        supplier_lookup = {row.value: row.label for row in self.list_supplier_options(active_only=None)}
        rows = sorted(
            self._purchasing_service.list_receipts(
                purchase_order_id=purchase_order_id,
                limit=limit,
            ),
            key=lambda row: str(getattr(row, "receipt_number", "") or "").casefold(),
            reverse=True,
        )
        return tuple(
            _serialize_receipt(
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
        storeroom_lookup = {row.value: row.label for row in self.list_storeroom_options(active_only=None)}
        rows = sorted(
            self._purchasing_service.list_receipt_lines(receipt_id),
            key=lambda row: int(getattr(row, "line_number", 0) or 0),
        )
        return tuple(
            _serialize_receipt_line(
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
        storeroom_lookup = {entry.value: entry.label for entry in self.list_storeroom_options(active_only=None)}
        return _serialize_requisition(
            row,
            site_lookup=site_lookup,
            storeroom_lookup=storeroom_lookup,
            requisition_lookup={row.id: clean_text(getattr(row, "requisition_number", ""))},
        )

    def _serialize_requisition_line(self, row) -> InventoryRequisitionLineDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_item_options(active_only=None)}
        supplier_lookup = {entry.value: entry.label for entry in self.list_supplier_options(active_only=None)}
        return _serialize_requisition_line(
            row,
            item_lookup=item_lookup,
            supplier_lookup=supplier_lookup,
        )

    def _serialize_purchase_order(self, row) -> InventoryPurchaseOrderDesktopDto:
        site_lookup = {entry.value: entry.label for entry in self.list_site_options(active_only=None)}
        supplier_lookup = {entry.value: entry.label for entry in self.list_supplier_options(active_only=None)}
        requisition_lookup = {
            entry.id: clean_text(getattr(entry, "requisition_number", ""))
            for entry in self.list_requisitions(status=None, limit=500)
        }
        return _serialize_purchase_order(
            row,
            site_lookup=site_lookup,
            supplier_lookup=supplier_lookup,
            requisition_lookup=requisition_lookup,
        )

    def _serialize_purchase_order_line(self, row) -> InventoryPurchaseOrderLineDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_item_options(active_only=None)}
        storeroom_lookup = {entry.value: entry.label for entry in self.list_storeroom_options(active_only=None)}
        return _serialize_purchase_order_line(
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
        supplier_lookup = {entry.value: entry.label for entry in self.list_supplier_options(active_only=None)}
        return _serialize_receipt(
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


def _serialize_requisition(
    row,
    *,
    site_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
    requisition_lookup: dict[str, str],
) -> InventoryRequisitionDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryRequisitionDesktopDto(
        id=row.id,
        requisition_number=clean_text(getattr(row, "requisition_number", "")),
        requesting_site_id=clean_text(getattr(row, "requesting_site_id", "")),
        requesting_site_label=site_lookup.get(clean_text(getattr(row, "requesting_site_id", "")), "-"),
        requesting_storeroom_id=clean_text(getattr(row, "requesting_storeroom_id", "")),
        requesting_storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "requesting_storeroom_id", "")), "-"),
        requester_username=clean_text(getattr(row, "requester_username", ""), default="-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        purpose=clean_text(getattr(row, "purpose", "")),
        needed_by_date=getattr(row, "needed_by_date", None),
        needed_by_date_label=format_date(getattr(row, "needed_by_date", None)),
        priority=clean_text(getattr(row, "priority", "")),
        approval_request_id=clean_text(getattr(row, "approval_request_id", "")) or None,
        source_reference_type=clean_text(getattr(row, "source_reference_type", "")),
        source_reference_id=clean_text(getattr(row, "source_reference_id", "")),
        submitted_at_label=format_datetime(getattr(row, "submitted_at", None)),
        approved_at_label=format_datetime(getattr(row, "approved_at", None)),
        cancelled_at_label=format_datetime(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def _serialize_requisition_line(
    row,
    *,
    item_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
) -> InventoryRequisitionLineDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    supplier_id = clean_text(getattr(row, "suggested_supplier_party_id", "")) or None
    return InventoryRequisitionLineDesktopDto(
        id=row.id,
        purchase_requisition_id=clean_text(getattr(row, "purchase_requisition_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        description=clean_text(getattr(row, "description", "")),
        quantity_requested=float(getattr(row, "quantity_requested", 0.0) or 0.0),
        quantity_requested_label=format_quantity(getattr(row, "quantity_requested", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        needed_by_date=getattr(row, "needed_by_date", None),
        needed_by_date_label=format_date(getattr(row, "needed_by_date", None)),
        estimated_unit_cost=float(getattr(row, "estimated_unit_cost", 0.0) or 0.0),
        estimated_unit_cost_label=format_amount(getattr(row, "estimated_unit_cost", 0.0)),
        quantity_sourced=float(getattr(row, "quantity_sourced", 0.0) or 0.0),
        quantity_sourced_label=format_quantity(getattr(row, "quantity_sourced", 0.0)),
        suggested_supplier_party_id=supplier_id,
        suggested_supplier_label=supplier_lookup.get(supplier_id or "", "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        notes=clean_text(getattr(row, "notes", "")),
    )


def _serialize_purchase_order(
    row,
    *,
    site_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
    requisition_lookup: dict[str, str],
) -> InventoryPurchaseOrderDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    source_requisition_id = clean_text(getattr(row, "source_requisition_id", "")) or None
    return InventoryPurchaseOrderDesktopDto(
        id=row.id,
        po_number=clean_text(getattr(row, "po_number", "")),
        site_id=clean_text(getattr(row, "site_id", "")),
        site_label=site_lookup.get(clean_text(getattr(row, "site_id", "")), "-"),
        supplier_party_id=clean_text(getattr(row, "supplier_party_id", "")),
        supplier_label=supplier_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        order_date=getattr(row, "order_date", None),
        order_date_label=format_date(getattr(row, "order_date", None)),
        expected_delivery_date=getattr(row, "expected_delivery_date", None),
        expected_delivery_date_label=format_date(getattr(row, "expected_delivery_date", None)),
        currency_code=clean_text(getattr(row, "currency_code", "")),
        approval_request_id=clean_text(getattr(row, "approval_request_id", "")) or None,
        source_requisition_id=source_requisition_id,
        source_requisition_label=requisition_lookup.get(source_requisition_id or "", "-"),
        supplier_reference=clean_text(getattr(row, "supplier_reference", "")),
        submitted_at_label=format_datetime(getattr(row, "submitted_at", None)),
        approved_at_label=format_datetime(getattr(row, "approved_at", None)),
        sent_at_label=format_datetime(getattr(row, "sent_at", None)),
        closed_at_label=format_datetime(getattr(row, "closed_at", None)),
        cancelled_at_label=format_datetime(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def _serialize_purchase_order_line(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryPurchaseOrderLineDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryPurchaseOrderLineDesktopDto(
        id=row.id,
        purchase_order_id=clean_text(getattr(row, "purchase_order_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        destination_storeroom_id=clean_text(getattr(row, "destination_storeroom_id", "")),
        destination_storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "destination_storeroom_id", "")), "-"),
        description=clean_text(getattr(row, "description", "")),
        quantity_ordered=float(getattr(row, "quantity_ordered", 0.0) or 0.0),
        quantity_ordered_label=format_quantity(getattr(row, "quantity_ordered", 0.0)),
        quantity_received=float(getattr(row, "quantity_received", 0.0) or 0.0),
        quantity_received_label=format_quantity(getattr(row, "quantity_received", 0.0)),
        quantity_rejected=float(getattr(row, "quantity_rejected", 0.0) or 0.0),
        quantity_rejected_label=format_quantity(getattr(row, "quantity_rejected", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_price=float(getattr(row, "unit_price", 0.0) or 0.0),
        unit_price_label=format_amount(getattr(row, "unit_price", 0.0)),
        expected_delivery_date=getattr(row, "expected_delivery_date", None),
        expected_delivery_date_label=format_date(getattr(row, "expected_delivery_date", None)),
        source_requisition_line_id=clean_text(getattr(row, "source_requisition_line_id", "")) or None,
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        notes=clean_text(getattr(row, "notes", "")),
    )


def _serialize_receipt(
    row,
    *,
    purchase_order_lookup: dict[str, str],
    site_lookup: dict[str, str],
    supplier_lookup: dict[str, str],
) -> InventoryReceiptDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryReceiptDesktopDto(
        id=row.id,
        receipt_number=clean_text(getattr(row, "receipt_number", "")),
        purchase_order_id=clean_text(getattr(row, "purchase_order_id", "")),
        purchase_order_label=purchase_order_lookup.get(clean_text(getattr(row, "purchase_order_id", "")), "-"),
        received_site_id=clean_text(getattr(row, "received_site_id", "")),
        received_site_label=site_lookup.get(clean_text(getattr(row, "received_site_id", "")), "-"),
        supplier_party_id=clean_text(getattr(row, "supplier_party_id", "")),
        supplier_label=supplier_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        receipt_date_label=format_datetime(getattr(row, "receipt_date", None)),
        supplier_delivery_reference=clean_text(getattr(row, "supplier_delivery_reference", "")),
        received_by_username=clean_text(getattr(row, "received_by_username", ""), default="-"),
        notes=clean_text(getattr(row, "notes", "")),
    )


def _serialize_receipt_line(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryReceiptLineDesktopDto:
    return InventoryReceiptLineDesktopDto(
        id=row.id,
        receipt_header_id=clean_text(getattr(row, "receipt_header_id", "")),
        purchase_order_line_id=clean_text(getattr(row, "purchase_order_line_id", "")),
        line_number=int(getattr(row, "line_number", 0) or 0),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        quantity_accepted=float(getattr(row, "quantity_accepted", 0.0) or 0.0),
        quantity_accepted_label=format_quantity(getattr(row, "quantity_accepted", 0.0)),
        quantity_rejected=float(getattr(row, "quantity_rejected", 0.0) or 0.0),
        quantity_rejected_label=format_quantity(getattr(row, "quantity_rejected", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_cost=float(getattr(row, "unit_cost", 0.0) or 0.0),
        unit_cost_label=format_amount(getattr(row, "unit_cost", 0.0)),
        lot_number=clean_text(getattr(row, "lot_number", "")),
        serial_number=clean_text(getattr(row, "serial_number", "")),
        expiry_date_label=format_date(getattr(row, "expiry_date", None)),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "InventoryProcurementProcurementDesktopApi",
    "InventoryProcurementStatusDescriptor",
    "InventoryPurchaseOrderCreateCommand",
    "InventoryPurchaseOrderDesktopDto",
    "InventoryPurchaseOrderLineCreateCommand",
    "InventoryPurchaseOrderLineDesktopDto",
    "InventoryPurchaseOrderUpdateCommand",
    "InventoryReceiptDesktopDto",
    "InventoryReceiptLineCommand",
    "InventoryReceiptLineDesktopDto",
    "InventoryReceiptPostCommand",
    "InventoryRequisitionCreateCommand",
    "InventoryRequisitionDesktopDto",
    "InventoryRequisitionLineCreateCommand",
    "InventoryRequisitionLineDesktopDto",
    "InventoryRequisitionUpdateCommand",
    "build_inventory_procurement_procurement_desktop_api",
]
