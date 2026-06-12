from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def to_requisition_line_record_view_model(row) -> InventoryRecordViewModel:
    remaining = max(
        0.0,
        float(row.quantity_requested or 0.0) - float(row.quantity_sourced or 0.0),
    )
    return InventoryRecordViewModel(
        id=row.id,
        title=f"L{row.line_number} - {row.stock_item_label}",
        status_label=row.status_label,
        subtitle=row.description or row.suggested_supplier_label or "-",
        supporting_text=(
            f"Requested {row.quantity_requested_label} | "
            f"Sourced {row.quantity_sourced_label} | "
            f"Remaining {remaining:,.3f}"
        ),
        meta_text=(
            f"Supplier {row.suggested_supplier_label or '-'} | "
            f"Estimated {row.estimated_unit_cost_label}"
        ),
        state={
            "requisitionLineId": row.id,
            "stockItemId": row.stock_item_id,
            "remainingQty": remaining,
        },
    )
