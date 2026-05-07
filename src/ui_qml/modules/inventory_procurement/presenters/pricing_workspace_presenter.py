from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementPricingDesktopApi,
    build_inventory_procurement_pricing_desktop_api,
)
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.pricing import (
    InventoryPricingWorkspaceViewModel,
)


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
        site_options = (
            InventorySelectorOptionViewModel(value="all", label="All sites"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_site_options(active_only=None)
            ),
        )
        storeroom_options = (
            InventorySelectorOptionViewModel(value="all", label="All storerooms"),
            *(
                InventorySelectorOptionViewModel(
                    value=option.value,
                    label=f"{option.label} ({option.site_label})",
                )
                for option in self._desktop_api.list_storeroom_options(active_only=None)
            ),
        )
        supplier_options = (
            InventorySelectorOptionViewModel(value="all", label="All suppliers"),
            *(
                InventorySelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_supplier_options(active_only=None)
            ),
        )
        limit_options = (
            InventorySelectorOptionViewModel(value="100", label="100 rows"),
            InventorySelectorOptionViewModel(value="200", label="200 rows"),
            InventorySelectorOptionViewModel(value="500", label="500 rows"),
        )
        normalized_site_filter = self._normalize_filter(site_filter, site_options)
        normalized_storeroom_filter = self._normalize_filter(
            storeroom_filter,
            storeroom_options,
        )
        normalized_supplier_filter = self._normalize_filter(
            supplier_filter,
            supplier_options,
        )
        normalized_limit_filter = self._normalize_filter(limit_filter, limit_options)
        snapshot = self._desktop_api.build_snapshot(
            site_id=None if normalized_site_filter == "all" else normalized_site_filter,
            storeroom_id=(
                None
                if normalized_storeroom_filter == "all"
                else normalized_storeroom_filter
            ),
            supplier_party_id=(
                None if normalized_supplier_filter == "all" else normalized_supplier_filter
            ),
            limit=int(normalized_limit_filter),
        )
        pricing_empty_state = (
            snapshot.empty_state
            or "No supplier price lines match the current filters."
        )
        stock_empty_state = (
            snapshot.empty_state or "No stock signals match the current filters."
        )
        return InventoryPricingWorkspaceViewModel(
            overview=InventoryCatalogOverviewViewModel(
                title=snapshot.title,
                subtitle=snapshot.subtitle,
                metrics=tuple(
                    InventoryCatalogMetricViewModel(
                        label=metric.label,
                        value=metric.value,
                        supporting_text=metric.supporting_text,
                    )
                    for metric in snapshot.metrics
                ),
            ),
            context_label=snapshot.context_label,
            site_options=site_options,
            storeroom_options=storeroom_options,
            supplier_options=supplier_options,
            limit_options=limit_options,
            selected_site_filter=normalized_site_filter,
            selected_storeroom_filter=normalized_storeroom_filter,
            selected_supplier_filter=normalized_supplier_filter,
            selected_limit_filter=normalized_limit_filter,
            stock_rows=tuple(
                InventoryRecordViewModel(
                    id=row.id,
                    title=row.title,
                    status_label=row.status_label,
                    subtitle=row.subtitle,
                    supporting_text=row.supporting_text,
                    meta_text=row.meta_text,
                    can_primary_action=False,
                    can_secondary_action=False,
                    can_tertiary_action=False,
                )
                for row in snapshot.stock_rows
            ),
            stock_empty_state=stock_empty_state,
            supplier_price_rows=tuple(
                InventoryRecordViewModel(
                    id=row.id,
                    title=row.title,
                    status_label=row.status_label,
                    subtitle=row.subtitle,
                    supporting_text=row.supporting_text,
                    meta_text=row.meta_text,
                    can_primary_action=False,
                    can_secondary_action=False,
                    can_tertiary_action=False,
                )
                for row in snapshot.supplier_price_rows
            ),
            supplier_price_empty_state=pricing_empty_state,
            can_export=snapshot.can_export,
            empty_state=snapshot.empty_state,
        )

    def export_stock_status_csv(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
    ) -> str:
        return self._desktop_api.export_stock_status_csv(
            output_path,
            site_id=None if site_filter == "all" else site_filter,
            storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
        )

    def export_stock_status_excel(
        self,
        output_path: str,
        *,
        site_filter: str,
        storeroom_filter: str,
    ) -> str:
        return self._desktop_api.export_stock_status_excel(
            output_path,
            site_id=None if site_filter == "all" else site_filter,
            storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
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
        return self._desktop_api.export_procurement_overview_csv(
            output_path,
            site_id=None if site_filter == "all" else site_filter,
            storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
            supplier_party_id=None if supplier_filter == "all" else supplier_filter,
            limit=int(limit_filter),
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
        return self._desktop_api.export_procurement_overview_excel(
            output_path,
            site_id=None if site_filter == "all" else site_filter,
            storeroom_id=None if storeroom_filter == "all" else storeroom_filter,
            supplier_party_id=None if supplier_filter == "all" else supplier_filter,
            limit=int(limit_filter),
        )

    @staticmethod
    def _normalize_filter(filter_value: str, options) -> str:
        normalized_input = (filter_value or "").strip().casefold()
        for option in options:
            if str(option.value or "").casefold() == normalized_input:
                return option.value
        return options[0].value if options else "all"


__all__ = ["InventoryPricingWorkspacePresenter"]
