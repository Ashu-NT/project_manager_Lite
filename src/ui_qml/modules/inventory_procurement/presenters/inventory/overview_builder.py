from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
)


def build_overview(
    *,
    all_storerooms,
    all_balances,
    filtered_storerooms,
    filtered_balances,
    filtered_transactions,
) -> InventoryCatalogOverviewViewModel:
    active_storerooms = sum(1 for row in all_storerooms if row.is_active)
    low_stock_count = sum(1 for row in all_balances if row.reorder_required)
    internal_supplier_count = sum(1 for row in all_storerooms if row.is_internal_supplier)
    return InventoryCatalogOverviewViewModel(
        title="Inventory",
        subtitle="Storeroom governance, stock position, and movement execution through the module-local inventory desktop API.",
        metrics=(
            InventoryCatalogMetricViewModel(
                label="Storerooms",
                value=str(len(all_storerooms)),
                supporting_text=f"{active_storerooms} active, showing {len(filtered_storerooms)} with current filters.",
            ),
            InventoryCatalogMetricViewModel(
                label="Internal suppliers",
                value=str(internal_supplier_count),
                supporting_text="Storerooms flagged to support internal supply or redistribution workflows.",
            ),
            InventoryCatalogMetricViewModel(
                label="Stock balances",
                value=str(len(all_balances)),
                supporting_text=f"{len(filtered_balances)} balances remain after the current filters.",
            ),
            InventoryCatalogMetricViewModel(
                label="Reorder watch",
                value=str(low_stock_count),
                supporting_text="Balances currently below reorder expectations.",
            ),
            InventoryCatalogMetricViewModel(
                label="Recent movements",
                value=str(len(filtered_transactions)),
                supporting_text="Latest stock transactions visible in the movement feed.",
            ),
        ),
    )
