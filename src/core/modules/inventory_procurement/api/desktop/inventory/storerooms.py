from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryStoreroomCreateCommand,
    InventoryStoreroomDesktopDto,
    InventoryStoreroomUpdateCommand,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.serializers import (
    serialize_storeroom,
)


class InventoryDesktopStoreroomMixin:
    def list_storerooms(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        search_text: str = "",
    ) -> tuple[InventoryStoreroomDesktopDto, ...]:
        if self._inventory_service is None:
            return ()
        site_lookup = {row.value: row.label for row in self.list_sites(active_only=None)}
        party_lookup = self._party_lookup()
        if search_text:
            rows = self._inventory_service.search_storerooms(
                search_text=search_text,
                active_only=active_only,
                site_id=site_id,
            )
        else:
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
            serialize_storeroom(
                row,
                site_lookup=site_lookup,
                party_lookup=party_lookup,
            )
            for row in ordered
        )

    def create_storeroom(
        self,
        command: InventoryStoreroomCreateCommand,
    ) -> InventoryStoreroomDesktopDto:
        storeroom = self._require_inventory_service().create_storeroom(
            storeroom_code=command.storeroom_code,
            name=command.name,
            site_id=command.site_id,
            description=command.description,
            status=command.status,
            storeroom_type=command.storeroom_type,
            is_internal_supplier=command.is_internal_supplier,
            allows_issue=command.allows_issue,
            allows_transfer=command.allows_transfer,
            allows_receiving=command.allows_receiving,
            requires_reservation_for_issue=command.requires_reservation_for_issue,
            requires_supplier_reference_for_receipt=command.requires_supplier_reference_for_receipt,
            default_currency_code=command.default_currency_code,
            manager_party_id=command.manager_party_id,
            notes=command.notes,
        )
        return self._serialize_storeroom(storeroom)

    def update_storeroom(
        self,
        command: InventoryStoreroomUpdateCommand,
    ) -> InventoryStoreroomDesktopDto:
        storeroom = self._require_inventory_service().update_storeroom(
            command.storeroom_id,
            storeroom_code=command.storeroom_code,
            name=command.name,
            site_id=command.site_id,
            description=command.description,
            status=command.status,
            storeroom_type=command.storeroom_type,
            is_internal_supplier=command.is_internal_supplier,
            allows_issue=command.allows_issue,
            allows_transfer=command.allows_transfer,
            allows_receiving=command.allows_receiving,
            requires_reservation_for_issue=command.requires_reservation_for_issue,
            requires_supplier_reference_for_receipt=command.requires_supplier_reference_for_receipt,
            default_currency_code=command.default_currency_code,
            manager_party_id=command.manager_party_id,
            notes=command.notes,
            expected_version=command.expected_version,
        )
        return self._serialize_storeroom(storeroom)

    def toggle_storeroom_active(
        self,
        storeroom_id: str,
        *,
        expected_version: int | None = None,
    ) -> InventoryStoreroomDesktopDto:
        service = self._require_inventory_service()
        storeroom = service.get_storeroom(storeroom_id)
        updated = service.update_storeroom(
            storeroom_id,
            is_active=not bool(getattr(storeroom, "is_active", True)),
            expected_version=expected_version,
        )
        return self._serialize_storeroom(updated)

    def _serialize_storeroom(self, row) -> InventoryStoreroomDesktopDto:
        site_lookup = {entry.value: entry.label for entry in self.list_sites(active_only=None)}
        return serialize_storeroom(
            row,
            site_lookup=site_lookup,
            party_lookup=self._party_lookup(),
        )


__all__ = ["InventoryDesktopStoreroomMixin"]
