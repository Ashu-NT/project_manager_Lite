from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def to_receipt_record_view_model(row, receipt_lines) -> InventoryRecordViewModel:
    accepted = sum(float(line.quantity_accepted or 0.0) for line in receipt_lines)
    rejected = sum(float(line.quantity_rejected or 0.0) for line in receipt_lines)
    return InventoryRecordViewModel(
        id=row.id,
        title=row.receipt_number,
        status_label=row.status_label,
        subtitle=f"{row.purchase_order_label} | {row.supplier_label}",
        supporting_text=f"Accepted {accepted:,.3f} | Rejected {rejected:,.3f}",
        meta_text=(
            f"Posted {row.receipt_date_label or '-'} | "
            f"Delivery ref {row.supplier_delivery_reference or '-'}"
        ),
    )
