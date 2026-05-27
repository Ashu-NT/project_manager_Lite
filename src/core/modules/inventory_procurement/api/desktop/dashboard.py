from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.common.reference_service import (
    InventoryReferenceService,
)
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryService,
    ReservationService,
    StockControlService,
)
from src.core.modules.inventory_procurement.application.procurement import (
    ProcurementService,
    PurchasingService,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_date,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockReservationStatus,
)
from src.core.modules.inventory_procurement.domain.procurement.purchasing import (
    PurchaseOrderStatus,
    PurchaseRequisitionStatus,
)


@dataclass(frozen=True)
class InventoryDashboardMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class InventoryDashboardRowDescriptor:
    id: str
    title: str
    subtitle: str = ""
    status_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class InventoryDashboardSectionDescriptor:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    rows: tuple[InventoryDashboardRowDescriptor, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class InventoryDashboardSnapshotDescriptor:
    title: str
    subtitle: str
    context_label: str
    metrics: tuple[InventoryDashboardMetricDescriptor, ...]
    sections: tuple[InventoryDashboardSectionDescriptor, ...]
    empty_state: str = ""


class InventoryProcurementDashboardDesktopApi:
    def __init__(
        self,
        *,
        item_service: ItemMasterService | None = None,
        inventory_service: InventoryService | None = None,
        stock_service: StockControlService | None = None,
        reservation_service: ReservationService | None = None,
        procurement_service: ProcurementService | None = None,
        purchasing_service: PurchasingService | None = None,
        reference_service: InventoryReferenceService | None = None,
    ) -> None:
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._stock_service = stock_service
        self._reservation_service = reservation_service
        self._procurement_service = procurement_service
        self._purchasing_service = purchasing_service
        self._reference_service = reference_service

    def build_empty_snapshot(self) -> InventoryDashboardSnapshotDescriptor:
        return InventoryDashboardSnapshotDescriptor(
            title="Inventory Dashboard",
            subtitle="Inventory overview and procurement pressure appear here once the desktop API is connected.",
            context_label="Context: not connected",
            metrics=(
                InventoryDashboardMetricDescriptor("Items", "0", "Active master records"),
                InventoryDashboardMetricDescriptor("Storerooms", "0", "Active stock locations"),
                InventoryDashboardMetricDescriptor("Stock Positions", "0", "Tracked balances"),
                InventoryDashboardMetricDescriptor("Open Reservations", "0", "Held demand"),
                InventoryDashboardMetricDescriptor("Awaiting Approval", "0", "Requisitions and POs"),
                InventoryDashboardMetricDescriptor("Receiving Queue", "0", "POs open for receipt"),
                InventoryDashboardMetricDescriptor("Low Stock", "0", "Reorder attention"),
                InventoryDashboardMetricDescriptor("On Order Qty", "0.000", "Approved inbound supply"),
            ),
            sections=(
                InventoryDashboardSectionDescriptor(
                    title="Inventory Dashboard Preview",
                    subtitle="The QML dashboard will render live inventory KPIs and queue sections here.",
                    empty_state="Inventory desktop API is not connected in this preview.",
                ),
            ),
            empty_state="Inventory desktop API is not connected in this preview.",
        )

    def build_snapshot(self) -> InventoryDashboardSnapshotDescriptor:
        if not all(
            (
                self._item_service,
                self._inventory_service,
                self._stock_service,
                self._reservation_service,
                self._procurement_service,
                self._purchasing_service,
            )
        ):
            return self.build_empty_snapshot()

        item_lookup = self._item_lookup()
        storeroom_lookup = self._storeroom_lookup()
        site_lookup = self._site_lookup()
        party_lookup = self._party_lookup()

        items = self._item_service.list_items(active_only=None)
        storerooms = self._inventory_service.list_storerooms(active_only=None)
        balances = self._stock_service.list_balances()
        reservations = self._reservation_service.list_reservations(limit=500)
        requisitions = self._procurement_service.list_requisitions(limit=500)
        purchase_orders = self._purchasing_service.list_purchase_orders(limit=500)
        receipts = self._purchasing_service.list_receipts(limit=200)

        low_stock_rows = tuple(
            InventoryDashboardRowDescriptor(
                id=balance.id,
                title=item_lookup.get(balance.stock_item_id, balance.stock_item_id),
                subtitle=storeroom_lookup.get(balance.storeroom_id, balance.storeroom_id),
                status_label="Reorder",
                supporting_text=(
                    f"Available {format_quantity(balance.available_qty)} {clean_text(balance.uom)} | "
                    f"On order {format_quantity(balance.on_order_qty)}"
                ),
                meta_text=f"Reserved {format_quantity(balance.reserved_qty)}",
                tone="warning",
            )
            for balance in sorted(
                [row for row in balances if bool(getattr(row, "reorder_required", False))],
                key=lambda row: (
                    float(getattr(row, "available_qty", 0.0) or 0.0),
                    float(getattr(row, "on_order_qty", 0.0) or 0.0),
                ),
            )[:12]
        )

        approval_rows = tuple(
            InventoryDashboardRowDescriptor(
                id=row.id,
                title=clean_text(
                    getattr(row, "requisition_number", "")
                    or getattr(row, "po_number", "")
                ),
                subtitle=_approval_subtitle(
                    row=row,
                    site_lookup=site_lookup,
                    storeroom_lookup=storeroom_lookup,
                    party_lookup=party_lookup,
                ),
                status_label=format_enum_label(
                    getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
                ),
                supporting_text=clean_text(getattr(row, "purpose", "") or getattr(row, "supplier_reference", ""), default="-"),
                meta_text=_approval_meta(row),
                tone="accent",
            )
            for row in (
                [
                    *[
                        req
                        for req in requisitions
                        if getattr(req, "status", None) in {
                            PurchaseRequisitionStatus.SUBMITTED,
                            PurchaseRequisitionStatus.UNDER_REVIEW,
                        }
                    ],
                    *[
                        po
                        for po in purchase_orders
                        if getattr(po, "status", None) in {
                            PurchaseOrderStatus.SUBMITTED,
                            PurchaseOrderStatus.UNDER_REVIEW,
                        }
                    ],
                ]
            )[:12]
        )

        receiving_rows = tuple(
            InventoryDashboardRowDescriptor(
                id=row.id,
                title=clean_text(getattr(row, "po_number", "")),
                subtitle=party_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
                status_label=format_enum_label(
                    getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
                ),
                supporting_text=site_lookup.get(clean_text(getattr(row, "site_id", "")), "-"),
                meta_text=(
                    f"Expected {format_date(getattr(row, 'expected_delivery_date', None))} | "
                    f"Receipts {sum(1 for receipt in receipts if getattr(receipt, 'purchase_order_id', '') == row.id)}"
                ),
                tone="success",
            )
            for row in [
                po
                for po in purchase_orders
                if getattr(po, "status", None) in {
                    PurchaseOrderStatus.APPROVED,
                    PurchaseOrderStatus.SENT,
                    PurchaseOrderStatus.PARTIALLY_RECEIVED,
                }
            ][:12]
        )

        open_reservations = [
            row
            for row in reservations
            if getattr(row, "status", None) in {
                StockReservationStatus.ACTIVE,
                StockReservationStatus.PARTIALLY_ISSUED,
            }
        ]
        active_items = [row for row in items if bool(getattr(row, "is_active", False))]
        active_storerooms = [row for row in storerooms if bool(getattr(row, "is_active", False))]
        awaiting_approval_count = len(approval_rows)
        receiving_queue_count = len(receiving_rows)
        low_stock_count = len(low_stock_rows)
        on_order_total = sum(float(getattr(row, "on_order_qty", 0.0) or 0.0) for row in balances)

        return InventoryDashboardSnapshotDescriptor(
            title="Inventory Dashboard",
            subtitle="Watch stock pressure, reservations, approvals, and receiving flow in one place.",
            context_label=f"Context: {len(active_storerooms)} active storerooms",
            metrics=(
                InventoryDashboardMetricDescriptor("Items", str(len(active_items)), "Active master records"),
                InventoryDashboardMetricDescriptor("Storerooms", str(len(active_storerooms)), "Active stock locations"),
                InventoryDashboardMetricDescriptor("Stock Positions", str(len(balances)), "Tracked balances"),
                InventoryDashboardMetricDescriptor("Open Reservations", str(len(open_reservations)), "Held demand"),
                InventoryDashboardMetricDescriptor("Awaiting Approval", str(awaiting_approval_count), "Requisitions and POs"),
                InventoryDashboardMetricDescriptor("Receiving Queue", str(receiving_queue_count), "POs open for receipt"),
                InventoryDashboardMetricDescriptor("Low Stock", str(low_stock_count), "Reorder attention"),
                InventoryDashboardMetricDescriptor("On Order Qty", format_quantity(on_order_total), "Approved inbound supply"),
            ),
            sections=(
                InventoryDashboardSectionDescriptor(
                    title="Low Stock Watch",
                    subtitle="Balances currently asking for replenishment.",
                    empty_state="No low-stock balances need attention right now.",
                    rows=low_stock_rows,
                ),
                InventoryDashboardSectionDescriptor(
                    title="Approval Queue",
                    subtitle="Submitted requisitions and purchase orders waiting on governance.",
                    empty_state="No requisitions or purchase orders are currently awaiting approval.",
                    rows=approval_rows,
                ),
                InventoryDashboardSectionDescriptor(
                    title="Receiving Queue",
                    subtitle="Approved and sent orders that still need receipts posted.",
                    empty_state="No approved or sent purchase orders are waiting for receiving.",
                    rows=receiving_rows,
                ),
            ),
        )

    def _item_lookup(self) -> dict[str, str]:
        if self._item_service is None:
            return {}
        return {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "item_code", "")),
                    clean_text(getattr(row, "name", "")),
                )
                if part
            )
            for row in self._item_service.list_items(active_only=None)
        }

    def _storeroom_lookup(self) -> dict[str, str]:
        if self._inventory_service is None:
            return {}
        return {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "storeroom_code", "")),
                    clean_text(getattr(row, "name", "")),
                )
                if part
            )
            for row in self._inventory_service.list_storerooms(active_only=None)
        }

    def _site_lookup(self) -> dict[str, str]:
        if self._reference_service is None:
            return {}
        return {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "site_code", "")),
                    clean_text(getattr(row, "name", "")),
                )
                if part
            )
            for row in self._reference_service.list_sites(active_only=None)
        }

    def _party_lookup(self) -> dict[str, str]:
        if self._reference_service is None:
            return {}
        return {
            row.id: " - ".join(
                part
                for part in (
                    clean_text(getattr(row, "party_code", "")),
                    clean_text(getattr(row, "party_name", "")),
                )
                if part
            )
            for row in self._reference_service.list_business_parties(active_only=None)
        }


def build_inventory_procurement_dashboard_desktop_api(
    *,
    item_service: ItemMasterService | None = None,
    inventory_service: InventoryService | None = None,
    stock_service: StockControlService | None = None,
    reservation_service: ReservationService | None = None,
    procurement_service: ProcurementService | None = None,
    purchasing_service: PurchasingService | None = None,
    reference_service: InventoryReferenceService | None = None,
) -> InventoryProcurementDashboardDesktopApi:
    return InventoryProcurementDashboardDesktopApi(
        item_service=item_service,
        inventory_service=inventory_service,
        stock_service=stock_service,
        reservation_service=reservation_service,
        procurement_service=procurement_service,
        purchasing_service=purchasing_service,
        reference_service=reference_service,
    )


def _approval_subtitle(
    *,
    row,
    site_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> str:
    if hasattr(row, "requesting_storeroom_id"):
        return " | ".join(
            part
            for part in (
                site_lookup.get(clean_text(getattr(row, "requesting_site_id", "")), "-"),
                storeroom_lookup.get(clean_text(getattr(row, "requesting_storeroom_id", "")), "-"),
            )
            if part
        )
    return " | ".join(
        part
        for part in (
            site_lookup.get(clean_text(getattr(row, "site_id", "")), "-"),
            party_lookup.get(clean_text(getattr(row, "supplier_party_id", "")), "-"),
        )
        if part
    )


def _approval_meta(row) -> str:
    if hasattr(row, "requesting_storeroom_id"):
        return f"Need by {format_date(getattr(row, 'needed_by_date', None))}"
    return f"Expected {format_date(getattr(row, 'expected_delivery_date', None))}"


__all__ = [
    "InventoryDashboardMetricDescriptor",
    "InventoryDashboardRowDescriptor",
    "InventoryDashboardSectionDescriptor",
    "InventoryDashboardSnapshotDescriptor",
    "InventoryProcurementDashboardDesktopApi",
    "build_inventory_procurement_dashboard_desktop_api",
]
