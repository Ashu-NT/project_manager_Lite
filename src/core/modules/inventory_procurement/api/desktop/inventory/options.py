from __future__ import annotations

from src.core.modules.inventory_procurement.application.common.support import (
    STOREROOM_STATUS_TRANSITIONS,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_enum_label,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryStoreroomStatusDescriptor,
    InventoryTransactionTypeDescriptor,
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
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockTransactionType,
)


class InventoryDesktopOptionMixin:
    def list_storeroom_statuses(self) -> tuple[InventoryStoreroomStatusDescriptor, ...]:
        return tuple(
            InventoryStoreroomStatusDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in STOREROOM_STATUS_TRANSITIONS
        )

    def list_transaction_types(self) -> tuple[InventoryTransactionTypeDescriptor, ...]:
        return tuple(
            InventoryTransactionTypeDescriptor(
                value=entry.value,
                label=format_enum_label(entry.value),
            )
            for entry in StockTransactionType
        )

    def list_sites(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventorySiteOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        sites = sorted(
            self._reference_service.list_sites(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "site_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_site_option(row) for row in sites)

    def list_items(
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
        site_id: str | None = None,
    ) -> tuple[InventoryStoreroomOptionDescriptor, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_sites(active_only=None)}
        rows = self._inventory_service.list_storerooms(
            active_only=active_only,
            site_id=site_id,
        )
        ordered = sorted(
            rows,
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "storeroom_code", "") or "").casefold(),
            ),
        )
        return tuple(
            serialize_storeroom_option(row, site_lookup=site_lookup) for row in ordered
        )

    def list_business_parties(
        self,
        *,
        active_only: bool | None = True,
    ) -> tuple[InventoryBusinessPartyOptionDescriptor, ...]:
        if self._reference_service is None:
            return ()
        parties = sorted(
            self._reference_service.list_business_parties(active_only=active_only),
            key=lambda row: (
                not bool(getattr(row, "is_active", True)),
                str(getattr(row, "party_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_business_party_option(row) for row in parties)

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


__all__ = ["InventoryDesktopOptionMixin"]
