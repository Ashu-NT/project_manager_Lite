from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.reservations.models import (
    InventoryReservationCreateCommand,
    InventoryReservationDesktopDto,
    InventoryReservationIssueCommand,
)
from src.core.modules.inventory_procurement.api.desktop.reservations.serializers import (
    serialize_reservation,
)


class InventoryReservationsDesktopRecordMixin:
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
        item_lookup = {
            row.value: row.label for row in self.list_item_options(active_only=None)
        }
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
            serialize_reservation(
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
        item_lookup = {
            entry.value: entry.label for entry in self.list_item_options(active_only=None)
        }
        storeroom_lookup = {
            entry.value: entry.label
            for entry in self.list_storeroom_options(active_only=None)
        }
        return serialize_reservation(
            row,
            item_lookup=item_lookup,
            storeroom_lookup=storeroom_lookup,
        )


__all__ = ["InventoryReservationsDesktopRecordMixin"]
