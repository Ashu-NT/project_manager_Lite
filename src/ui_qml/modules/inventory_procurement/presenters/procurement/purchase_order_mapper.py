from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def to_purchase_order_record_view_model(row) -> InventoryRecordViewModel:
    return InventoryRecordViewModel(
        id=row.id,
        title=row.po_number,
        status_label=row.status_label,
        subtitle=f"{row.site_label} | {row.supplier_label}",
        supporting_text=(
            f"Currency {row.currency_code or '-'} | "
            f"Expected {row.expected_delivery_date_label or '-'}"
        ),
        meta_text=(
            f"Source {row.source_requisition_label or '-'} | "
            f"Supplier Ref {row.supplier_reference or '-'}"
        ),
        state={
            "purchaseOrderId": row.id,
            "siteId": row.site_id,
            "siteLabel": row.site_label,
            "supplierPartyId": row.supplier_party_id,
            "supplierLabel": row.supplier_label,
            "currencyCode": row.currency_code,
            "sourceRequisitionId": row.source_requisition_id or "",
            "status": row.status,
            "version": row.version,
        },
    )
