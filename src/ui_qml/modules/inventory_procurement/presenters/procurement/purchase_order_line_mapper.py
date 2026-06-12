from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def purchase_order_line_outstanding(row) -> float:
    return max(
        0.0,
        float(row.quantity_ordered or 0.0)
        - float(row.quantity_received or 0.0)
        - float(row.quantity_rejected or 0.0),
    )


def to_purchase_order_line_record_view_model(row) -> InventoryRecordViewModel:
    outstanding = purchase_order_line_outstanding(row)
    return InventoryRecordViewModel(
        id=row.id,
        title=f"L{row.line_number} - {row.stock_item_label}",
        status_label=row.status_label,
        subtitle=row.destination_storeroom_label,
        supporting_text=(
            f"Ordered {row.quantity_ordered_label} | "
            f"Received {row.quantity_received_label} | "
            f"Rejected {row.quantity_rejected_label}"
        ),
        meta_text=f"Outstanding {outstanding:,.3f} | Unit price {row.unit_price_label}",
        state={
            "purchaseOrderLineId": row.id,
            "stockItemId": row.stock_item_id,
            "destinationStoreroomId": row.destination_storeroom_id,
            "outstandingQty": outstanding,
            "uom": row.uom,
            "unitPrice": row.unit_price,
        },
    )
