from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
)


def build_overview(
    *,
    all_requisitions,
    filtered_requisitions,
    all_purchase_orders,
    filtered_purchase_orders,
    all_receipts,
) -> InventoryCatalogOverviewViewModel:
    awaiting_requisition_count = sum(
        1 for row in all_requisitions if row.status in {"SUBMITTED", "UNDER_REVIEW"}
    )
    awaiting_purchase_order_count = sum(
        1 for row in all_purchase_orders if row.status in {"SUBMITTED", "UNDER_REVIEW"}
    )
    open_receiving_count = sum(
        1
        for row in all_purchase_orders
        if row.status in {"APPROVED", "SENT", "PARTIALLY_RECEIVED"}
    )
    return InventoryCatalogOverviewViewModel(
        title="Procurement",
        subtitle=(
            "Requisitions, supplier commitments, and receipt posting now run "
            "through the module-local procurement desktop API."
        ),
        metrics=(
            InventoryCatalogMetricViewModel(
                label="Requisitions",
                value=str(len(all_requisitions)),
                supporting_text=(
                    f"Showing {len(filtered_requisitions)} requisitions with the current filters."
                ),
            ),
            InventoryCatalogMetricViewModel(
                label="Purchase Orders",
                value=str(len(all_purchase_orders)),
                supporting_text=(
                    f"Showing {len(filtered_purchase_orders)} purchase orders with the current filters."
                ),
            ),
            InventoryCatalogMetricViewModel(
                label="Awaiting Approval",
                value=str(awaiting_requisition_count + awaiting_purchase_order_count),
                supporting_text=(
                    "Combined requisitions and purchase orders still moving through approvals."
                ),
            ),
            InventoryCatalogMetricViewModel(
                label="Open Receiving",
                value=str(open_receiving_count),
                supporting_text=f"{len(all_receipts)} receipts already posted.",
            ),
        ),
    )
