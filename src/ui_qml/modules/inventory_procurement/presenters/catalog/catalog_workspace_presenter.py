from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementCatalogDesktopApi,
    build_inventory_procurement_catalog_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogWorkspaceViewModel,
)

from .category_command_handler import (
    create_category,
    suggest_category_code,
    toggle_category_active,
    update_category,
)
from .document_command_handler import link_document, unlink_document
from .item_command_handler import (
    apply_bulk_status,
    create_item,
    suggest_item_code,
    toggle_item_active,
    update_item,
)
from .workspace_builder import build_workspace_state as _build_workspace_state

class InventoryCatalogWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementCatalogDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_catalog_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        active_filter: str = "all",
        usage_filter: str = "all",
        category_type_filter: str = "all",
        category_filter: str = "all",
        selected_category_id: str | None = None,
        selected_item_id: str | None = None,
    ) -> InventoryCatalogWorkspaceViewModel:
        return _build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            active_filter=active_filter,
            usage_filter=usage_filter,
            category_type_filter=category_type_filter,
            category_filter=category_filter,
            selected_category_id=selected_category_id,
            selected_item_id=selected_item_id,
        )

    def suggest_category_code(self, payload: dict[str, Any]) -> str:
        return suggest_category_code(self._desktop_api, payload)

    def suggest_item_code(self, payload: dict[str, Any]) -> str:
        return suggest_item_code(self._desktop_api, payload)

    def create_category(self, payload: dict[str, Any]) -> None:
        create_category(self._desktop_api, payload)

    def update_category(self, payload: dict[str, Any]) -> None:
        update_category(self._desktop_api, payload)

    def toggle_category_active(
        self,
        category_id: str,
        expected_version: int | None = None,
    ) -> None:
        toggle_category_active(self._desktop_api, category_id, expected_version)

    def create_item(self, payload: dict[str, Any]) -> None:
        create_item(self._desktop_api, payload)

    def update_item(self, payload: dict[str, Any]) -> None:
        update_item(self._desktop_api, payload)

    def apply_bulk_status(self, payload: dict[str, Any]) -> None:
        apply_bulk_status(self._desktop_api, payload)

    def toggle_item_active(
        self,
        item_id: str,
        expected_version: int | None = None,
    ) -> None:
        toggle_item_active(self._desktop_api, item_id, expected_version)

    def link_document(self, item_id: str, document_id: str) -> None:
        link_document(self._desktop_api, item_id, document_id)

    def unlink_document(self, item_id: str, document_id: str) -> None:
        unlink_document(self._desktop_api, item_id, document_id)

__all__ = ["InventoryCatalogWorkspacePresenter"]
