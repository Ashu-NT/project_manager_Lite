from __future__ import annotations

from src.core.modules.inventory_procurement.application.common.support import (
    ITEM_CATEGORY_TYPES,
    ITEM_STATUS_TRANSITIONS,
)
from src.core.modules.inventory_procurement.api.desktop._support import (
    format_enum_label,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.models import (
    InventoryCategoryTypeDescriptor,
    InventoryItemStatusDescriptor,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryBusinessPartyOptionDescriptor,
    serialize_business_party_option,
)


class InventoryCatalogDesktopOptionMixin:
    def list_category_types(self) -> tuple[InventoryCategoryTypeDescriptor, ...]:
        return tuple(
            InventoryCategoryTypeDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in sorted(ITEM_CATEGORY_TYPES)
        )

    def list_item_statuses(self) -> tuple[InventoryItemStatusDescriptor, ...]:
        return tuple(
            InventoryItemStatusDescriptor(
                value=value,
                label=format_enum_label(value),
            )
            for value in ITEM_STATUS_TRANSITIONS
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
                str(getattr(row, "party_name", "") or "").casefold(),
                str(getattr(row, "party_code", "") or "").casefold(),
            ),
        )
        return tuple(serialize_business_party_option(row) for row in parties)


__all__ = ["InventoryCatalogDesktopOptionMixin"]
