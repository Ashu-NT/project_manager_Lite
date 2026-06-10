from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementInventoryDesktopApi,
    build_inventory_procurement_inventory_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.inventory import (
    InventoryInventoryWorkspaceViewModel,
)

from .cycle_count_handler import complete_cycle_count, schedule_cycle_count
from .inventory_transaction_handler import (
    issue_stock,
    post_adjustment,
    post_opening_balance,
    return_stock,
    transfer_stock,
)
from .location_command_handler import create_location, update_location
from .reorder_policy_handler import upsert_reorder_policy
from .storeroom_command_handler import (
    create_storeroom,
    suggest_storeroom_code,
    toggle_storeroom_active,
    update_storeroom,
)
from .workspace_builder import build_workspace_state


class InventoryInventoryWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementInventoryDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_inventory_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        active_filter: str = "all",
        storeroom_filter: str = "all",
        item_filter: str = "all",
        transaction_type_filter: str = "all",
        selected_storeroom_id: str | None = None,
        selected_balance_id: str | None = None,
    ) -> InventoryInventoryWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            site_filter=site_filter,
            active_filter=active_filter,
            storeroom_filter=storeroom_filter,
            item_filter=item_filter,
            transaction_type_filter=transaction_type_filter,
            selected_storeroom_id=selected_storeroom_id,
            selected_balance_id=selected_balance_id,
        )

    def suggest_storeroom_code(self, payload: dict[str, Any]) -> str:
        return suggest_storeroom_code(self._desktop_api, payload)

    def create_storeroom(self, payload: dict[str, Any]) -> None:
        create_storeroom(self._desktop_api, payload)

    def update_storeroom(self, payload: dict[str, Any]) -> None:
        update_storeroom(self._desktop_api, payload)

    def toggle_storeroom_active(
        self,
        storeroom_id: str,
        expected_version: int | None = None,
    ) -> None:
        toggle_storeroom_active(self._desktop_api, storeroom_id, expected_version)

    def post_opening_balance(self, payload: dict[str, Any]) -> None:
        post_opening_balance(self._desktop_api, payload)

    def post_adjustment(self, payload: dict[str, Any]) -> None:
        post_adjustment(self._desktop_api, payload)

    def issue_stock(self, payload: dict[str, Any]) -> None:
        issue_stock(self._desktop_api, payload)

    def return_stock(self, payload: dict[str, Any]) -> None:
        return_stock(self._desktop_api, payload)

    def transfer_stock(self, payload: dict[str, Any]) -> None:
        transfer_stock(self._desktop_api, payload)

    def create_location(self, payload: dict[str, Any]) -> None:
        create_location(self._desktop_api, payload)

    def update_location(self, payload: dict[str, Any]) -> None:
        update_location(self._desktop_api, payload)

    def upsert_reorder_policy(self, payload: dict[str, Any]) -> None:
        upsert_reorder_policy(self._desktop_api, payload)

    def schedule_cycle_count(self, payload: dict[str, Any]) -> None:
        schedule_cycle_count(self._desktop_api, payload)

    def complete_cycle_count(self, payload: dict[str, Any]) -> None:
        complete_cycle_count(self._desktop_api, payload)
