from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_enum_label,
)
from src.core.modules.inventory_procurement.api.desktop.reservations.models import (
    InventoryReservationStatusDescriptor,
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


class InventoryReservationsDesktopOptionMixin:
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


__all__ = ["InventoryReservationsDesktopOptionMixin"]
