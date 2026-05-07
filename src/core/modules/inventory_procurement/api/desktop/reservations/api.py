from __future__ import annotations

from src.core.modules.inventory_procurement.application.catalog import ItemMasterService
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryService,
    ReservationService,
)
from src.core.modules.inventory_procurement.api.desktop.reservations.options import (
    InventoryReservationsDesktopOptionMixin,
)
from src.core.modules.inventory_procurement.api.desktop.reservations.records import (
    InventoryReservationsDesktopRecordMixin,
)


class InventoryProcurementReservationsDesktopApi(
    InventoryReservationsDesktopOptionMixin,
    InventoryReservationsDesktopRecordMixin,
):
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


__all__ = [
    "InventoryProcurementReservationsDesktopApi",
    "build_inventory_procurement_reservations_desktop_api",
]
