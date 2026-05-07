from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryService,
    ReservationService,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_date,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryCatalogItemOptionDescriptor,
    InventoryStoreroomOptionDescriptor,
    serialize_item_option,
    serialize_storeroom_option,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockReservationStatus,
)


@dataclass(frozen=True)
class InventoryReservationStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class InventoryReservationDesktopDto:
    id: str
    reservation_number: str
    stock_item_id: str
    stock_item_label: str
    storeroom_id: str
    storeroom_label: str
    reserved_qty: float
    reserved_qty_label: str
    issued_qty: float
    issued_qty_label: str
    remaining_qty: float
    remaining_qty_label: str
    uom: str
    status: str
    status_label: str
    need_by_date: date | None
    need_by_date_label: str
    source_reference_type: str
    source_reference_id: str
    requested_by_username: str
    created_at_label: str
    released_at_label: str
    cancelled_at_label: str
    notes: str
    version: int


@dataclass(frozen=True)
class InventoryReservationCreateCommand:
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    uom: str | None = None
    need_by_date: date | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    notes: str = ""


@dataclass(frozen=True)
class InventoryReservationIssueCommand:
    reservation_id: str
    quantity: float
    note: str = ""


class InventoryProcurementReservationsDesktopApi:
    def __init__(
        self,
        *,
        reservation_service: ReservationService | None = None,
        item_service: ItemMasterService | None = None,
        inventory_service: InventoryService | None = None,
    ) -> None:
        self._reservation_service = reservation_service
        self._item_service = item_service
        self._inventory_service = inventory_service

    def list_statuses(self) -> tuple[InventoryReservationStatusDescriptor, ...]:
        return tuple(
            InventoryReservationStatusDescriptor(
                value=status.value,
                label=format_enum_label(status.value),
            )
            for status in StockReservationStatus
        )

    def list_item_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryCatalogItemOptionDescriptor, ...]:
        if self._item_service is None:
            return ()
        items = sorted(
            self._item_service.list_items(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "item_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_item_option(row) for row in items)

    def list_storeroom_options(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        storerooms = sorted(
            self._inventory_service.list_storerooms(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "storeroom_code", "") or "").casefold(),
            ),
        )
        site_lookup = {
            clean_text(getattr(row, "site_id", "")): clean_text(
                getattr(row, "site_id", ""),
                default="-",
            )
            for row in storerooms
        }
        return tuple(
            serialize_storeroom_option(row, site_lookup=site_lookup)
            for row in storerooms
        )

    def list_reservations(
        self,
        *,
        stock_item_id: str | None = None,
        storeroom_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> tuple[InventoryReservationDesktopDto, ...]:
        if self._reservation_service is None:
            return ()
        item_lookup = {row.value: row.label for row in self.list_item_options(active_only=None)}
        storeroom_lookup = {
            row.value: row.label
            for row in self.list_storeroom_options(active_only=None)
        }
        reservations = self._reservation_service.list_reservations(
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            status=status,
            limit=limit,
        )
        ordered = sorted(
            reservations,
            key=lambda row: (
                str(getattr(row, "status", "")).casefold(),
                str(getattr(row, "reservation_number", "")).casefold(),
            ),
        )
        return tuple(
            _serialize_reservation(
                row,
                item_lookup=item_lookup,
                storeroom_lookup=storeroom_lookup,
            )
            for row in ordered
        )

    def create_reservation(
        self,
        command: InventoryReservationCreateCommand,
    ) -> InventoryReservationDesktopDto:
        service = self._require_reservation_service()
        reservation = service.create_reservation(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            reserved_qty=command.reserved_qty,
            uom=command.uom,
            need_by_date=command.need_by_date,
            source_reference_type=command.source_reference_type,
            source_reference_id=command.source_reference_id,
            notes=command.notes,
        )
        return self._serialize_reservation(reservation)

    def issue_reserved_stock(
        self,
        command: InventoryReservationIssueCommand,
    ) -> InventoryReservationDesktopDto:
        reservation = self._require_reservation_service().issue_reserved_stock(
            command.reservation_id,
            quantity=command.quantity,
            note=command.note,
        )
        return self._serialize_reservation(reservation)

    def release_reservation(
        self,
        reservation_id: str,
        *,
        note: str = "",
    ) -> InventoryReservationDesktopDto:
        reservation = self._require_reservation_service().release_reservation(
            reservation_id,
            note=note,
        )
        return self._serialize_reservation(reservation)

    def cancel_reservation(
        self,
        reservation_id: str,
        *,
        note: str = "",
    ) -> InventoryReservationDesktopDto:
        reservation = self._require_reservation_service().cancel_reservation(
            reservation_id,
            note=note,
        )
        return self._serialize_reservation(reservation)

    def _serialize_reservation(self, row) -> InventoryReservationDesktopDto:
        item_lookup = {entry.value: entry.label for entry in self.list_item_options(active_only=None)}
        storeroom_lookup = {
            entry.value: entry.label
            for entry in self.list_storeroom_options(active_only=None)
        }
        return _serialize_reservation(
            row,
            item_lookup=item_lookup,
            storeroom_lookup=storeroom_lookup,
        )

    def _require_reservation_service(self) -> ReservationService:
        if self._reservation_service is None:
            raise RuntimeError("Inventory reservations desktop API is not connected.")
        return self._reservation_service


def build_inventory_procurement_reservations_desktop_api(
    *,
    reservation_service: ReservationService | None = None,
    item_service: ItemMasterService | None = None,
    inventory_service: InventoryService | None = None,
) -> InventoryProcurementReservationsDesktopApi:
    return InventoryProcurementReservationsDesktopApi(
        reservation_service=reservation_service,
        item_service=item_service,
        inventory_service=inventory_service,
    )


def _serialize_reservation(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryReservationDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    return InventoryReservationDesktopDto(
        id=row.id,
        reservation_number=clean_text(getattr(row, "reservation_number", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        reserved_qty=float(getattr(row, "reserved_qty", 0.0) or 0.0),
        reserved_qty_label=format_quantity(getattr(row, "reserved_qty", 0.0)),
        issued_qty=float(getattr(row, "issued_qty", 0.0) or 0.0),
        issued_qty_label=format_quantity(getattr(row, "issued_qty", 0.0)),
        remaining_qty=float(getattr(row, "remaining_qty", 0.0) or 0.0),
        remaining_qty_label=format_quantity(getattr(row, "remaining_qty", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        need_by_date=getattr(row, "need_by_date", None),
        need_by_date_label=format_date(getattr(row, "need_by_date", None)),
        source_reference_type=clean_text(getattr(row, "source_reference_type", "")),
        source_reference_id=clean_text(getattr(row, "source_reference_id", "")),
        requested_by_username=clean_text(getattr(row, "requested_by_username", ""), default="-"),
        created_at_label=format_date(getattr(row, "created_at", None)),
        released_at_label=format_date(getattr(row, "released_at", None)),
        cancelled_at_label=format_date(getattr(row, "cancelled_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


__all__ = [
    "InventoryProcurementReservationsDesktopApi",
    "InventoryReservationCreateCommand",
    "InventoryReservationDesktopDto",
    "InventoryReservationIssueCommand",
    "InventoryReservationStatusDescriptor",
    "build_inventory_procurement_reservations_desktop_api",
]
