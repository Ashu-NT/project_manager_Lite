from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementPricingDesktopApi,
    build_inventory_procurement_pricing_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.pricing import (
    InventoryPricingWorkspaceViewModel,
)

from .export_handler import (
    export_procurement_overview_csv,
    export_procurement_overview_excel,
    export_stock_status_csv,
    export_stock_status_excel,
)
from .workspace_builder import build_workspace_state


class InventoryPricingWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: InventoryProcurementPricingDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_inventory_procurement_pricing_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_filter: str = "all",
        storeroom_filter: str = "all",
        supplier_filter: str = "all",
        limit_filter: str = "200",
    ) -> InventoryPricingWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
            supplier_filter=supplier_filter,
            limit_filter=limit_filter,
        )

    def export_stock_status_csv(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
    ) -> str:
        return export_stock_status_csv(
            self._desktop_api,
            output_path,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
        )

    def export_stock_status_excel(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
    ) -> str:
        return export_stock_status_excel(
            self._desktop_api,
            output_path,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
        )

    def export_procurement_overview_csv(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
        supplier_filter: str,
        limit_filter: str,
    ) -> str:
        return export_procurement_overview_csv(
            self._desktop_api,
            output_path,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
            supplier_filter=supplier_filter,
            limit_filter=limit_filter,
        )

    def export_procurement_overview_excel(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
        supplier_filter: str,
        limit_filter: str,
    ) -> str:
        return export_procurement_overview_excel(
            self._desktop_api,
            output_path,
            site_filter=site_filter,
            storeroom_filter=storeroom_filter,
            supplier_filter=supplier_filter,
            limit_filter=limit_filter,
        )
