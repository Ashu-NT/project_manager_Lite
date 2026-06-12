from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
)


def build_overview(
    *,
    all_reservations,
    filtered_reservations,
) -> InventoryCatalogOverviewViewModel:
    active_count = sum(
        1
        for row in all_reservations
        if row.status in {"ACTIVE", "PARTIALLY_ISSUED"}
        and float(row.remaining_qty or 0.0) > 0
    )
    issued_count = sum(
        1 for row in all_reservations if row.status in {"PARTIALLY_ISSUED", "FULLY_ISSUED"}
    )
    closed_count = sum(
        1 for row in all_reservations if row.status in {"RELEASED", "CANCELLED"}
    )
    return InventoryCatalogOverviewViewModel(
        title="Reservations",
        subtitle="Stock demand holds, issue execution, and release or cancellation flows through the module-local reservations desktop API.",
        metrics=(
            InventoryCatalogMetricViewModel(
                label="Reservations",
                value=str(len(all_reservations)),
                supporting_text=f"Showing {len(filtered_reservations)} reservations with the current filters.",
            ),
            InventoryCatalogMetricViewModel(
                label="Active",
                value=str(active_count),
                supporting_text="Open demand holds still consuming available stock.",
            ),
            InventoryCatalogMetricViewModel(
                label="Issued",
                value=str(issued_count),
                supporting_text="Reservations with at least some stock already issued.",
            ),
            InventoryCatalogMetricViewModel(
                label="Closed",
                value=str(closed_count),
                supporting_text="Reservations already released or cancelled.",
            ),
        ),
    )
