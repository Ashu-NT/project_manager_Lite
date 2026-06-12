from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementReservationsDesktopApi,
    build_inventory_procurement_reservations_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.reservations import (
    InventoryReservationsWorkspaceViewModel,
)

from .reservation_command_handler import (
    cancel_reservation,
    create_reservation,
    issue_reservation,
    release_reservation,
)
from .workspace_builder import build_workspace_state

class InventoryReservationsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementReservationsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = (
            desktop_api or build_inventory_procurement_reservations_desktop_api()
        )

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        status_filter: str = "all",
        item_filter: str = "all",
        storeroom_filter: str = "all",
        selected_reservation_id: str | None = None,
    ) -> InventoryReservationsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            status_filter=status_filter,
            item_filter=item_filter,
            storeroom_filter=storeroom_filter,
            selected_reservation_id=selected_reservation_id,
        )

    def create_reservation(self, payload: dict[str, Any]) -> None:
        create_reservation(self._desktop_api, payload)

    def issue_reservation(self, payload: dict[str, Any]) -> None:
        issue_reservation(self._desktop_api, payload)

    def release_reservation(self, reservation_id: str, note: str = "") -> None:
        release_reservation(self._desktop_api, reservation_id, note)

    def cancel_reservation(self, reservation_id: str, note: str = "") -> None:
        cancel_reservation(self._desktop_api, reservation_id, note)
