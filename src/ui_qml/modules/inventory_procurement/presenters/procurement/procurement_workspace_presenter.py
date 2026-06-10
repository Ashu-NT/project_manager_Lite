from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementProcurementDesktopApi,
    build_inventory_procurement_procurement_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.procurement import (
    InventoryProcurementProcurementWorkspaceViewModel,
)

from .purchase_order_command_handler import (
    add_purchase_order_line,
    cancel_purchase_order,
    close_purchase_order,
    create_purchase_order,
    send_purchase_order,
    submit_purchase_order,
    update_purchase_order,
)
from .receipt_command_handler import post_receipt
from .requisition_command_handler import (
    add_requisition_line,
    cancel_requisition,
    create_requisition,
    submit_requisition,
    update_requisition,
)
from .workspace_builder import build_workspace_state


class InventoryProcurementProcurementWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementProcurementDesktopApi | None = None,
    ) -> None:
        self._desktop_api = (
            desktop_api or build_inventory_procurement_procurement_desktop_api()
        )

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        storeroom_filter: str = "all",
        supplier_filter: str = "all",
        requisition_status_filter: str = "all",
        purchase_order_status_filter: str = "all",
        selected_requisition_id: str | None = None,
        selected_purchase_order_id: str | None = None,
    ) -> InventoryProcurementProcurementWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
            supplier_filter=supplier_filter,
            requisition_status_filter=requisition_status_filter,
            purchase_order_status_filter=purchase_order_status_filter,
            selected_requisition_id=selected_requisition_id,
            selected_purchase_order_id=selected_purchase_order_id,
        )

    def create_requisition(self, payload: dict[str, Any]) -> None:
        create_requisition(self._desktop_api, payload)

    def update_requisition(self, payload: dict[str, Any]) -> None:
        update_requisition(self._desktop_api, payload)

    def add_requisition_line(self, payload: dict[str, Any]) -> None:
        add_requisition_line(self._desktop_api, payload)

    def submit_requisition(self, requisition_id: str) -> None:
        submit_requisition(self._desktop_api, requisition_id)

    def cancel_requisition(self, requisition_id: str) -> None:
        cancel_requisition(self._desktop_api, requisition_id)

    def create_purchase_order(self, payload: dict[str, Any]) -> None:
        create_purchase_order(self._desktop_api, payload)

    def update_purchase_order(self, payload: dict[str, Any]) -> None:
        update_purchase_order(self._desktop_api, payload)

    def add_purchase_order_line(self, payload: dict[str, Any]) -> None:
        add_purchase_order_line(self._desktop_api, payload)

    def submit_purchase_order(self, purchase_order_id: str) -> None:
        submit_purchase_order(self._desktop_api, purchase_order_id)

    def send_purchase_order(self, purchase_order_id: str) -> None:
        send_purchase_order(self._desktop_api, purchase_order_id)

    def cancel_purchase_order(self, purchase_order_id: str) -> None:
        cancel_purchase_order(self._desktop_api, purchase_order_id)

    def close_purchase_order(self, purchase_order_id: str) -> None:
        close_purchase_order(self._desktop_api, purchase_order_id)

    def post_receipt(self, payload: dict[str, Any]) -> None:
        post_receipt(self._desktop_api, payload)
