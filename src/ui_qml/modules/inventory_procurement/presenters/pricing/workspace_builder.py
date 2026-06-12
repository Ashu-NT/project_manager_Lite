from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.pricing import (
    InventoryPricingWorkspaceViewModel,
)

from .filtering import normalize_filter
from .overview_builder import build_overview
from .record_mapper import to_record_view_model


def build_workspace_state(
    desktop_api,
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
            for option in desktop_api.list_site_options(active_only=None)
        ),
    )
    storeroom_options = (
        InventorySelectorOptionViewModel(value="all", label="All storerooms"),
        *(
            InventorySelectorOptionViewModel(
                value=option.value,
                label=f"{option.label} ({option.site_label})",
            )
            for option in desktop_api.list_storeroom_options(active_only=None)
        ),
    )
    supplier_options = (
        InventorySelectorOptionViewModel(value="all", label="All suppliers"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_supplier_options(active_only=None)
        ),
    )
    limit_options = (
        InventorySelectorOptionViewModel(value="100", label="100 rows"),
        InventorySelectorOptionViewModel(value="200", label="200 rows"),
        InventorySelectorOptionViewModel(value="500", label="500 rows"),
    )

    normalized_site_filter = normalize_filter(site_filter, site_options)
    normalized_storeroom_filter = normalize_filter(storeroom_filter, storeroom_options)
    normalized_supplier_filter = normalize_filter(supplier_filter, supplier_options)
    normalized_limit_filter = normalize_filter(limit_filter, limit_options)

    snapshot = desktop_api.build_snapshot(
        site_id=None if normalized_site_filter == "all" else normalized_site_filter,
        storeroom_id=(
            None if normalized_storeroom_filter == "all" else normalized_storeroom_filter
        ),
        supplier_party_id=(
            None if normalized_supplier_filter == "all" else normalized_supplier_filter
        ),
        limit=int(normalized_limit_filter),
    )

    pricing_empty_state = (
        snapshot.empty_state or "No supplier price lines match the current filters."
    )
    stock_empty_state = snapshot.empty_state or "No stock signals match the current filters."

    return InventoryPricingWorkspaceViewModel(
        overview=build_overview(snapshot),
        context_label=snapshot.context_label,
        site_options=site_options,
        storeroom_options=storeroom_options,
        supplier_options=supplier_options,
        limit_options=limit_options,
        selected_site_filter=normalized_site_filter,
        selected_storeroom_filter=normalized_storeroom_filter,
        selected_supplier_filter=normalized_supplier_filter,
        selected_limit_filter=normalized_limit_filter,
        stock_rows=tuple(to_record_view_model(row) for row in snapshot.stock_rows),
        stock_empty_state=stock_empty_state,
        supplier_price_rows=tuple(
            to_record_view_model(row) for row in snapshot.supplier_price_rows
        ),
        supplier_price_empty_state=pricing_empty_state,
        can_export=snapshot.can_export,
        empty_state=snapshot.empty_state,
    )
