from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
)

from .purchase_order_line_mapper import purchase_order_line_outstanding


def build_purchase_order_detail(row, purchase_order_lines) -> InventoryDetailViewModel:
    if row is None:
        return InventoryDetailViewModel(
            title="No purchase order selected",
            empty_state=(
                "Select a purchase order to review supplier commitments, manage "
                "lines, or post receipts."
            ),
        )
    is_draft = row.status == "DRAFT"
    outstanding_lines = sum(
        1 for line in purchase_order_lines if purchase_order_line_outstanding(line) > 0
    )
    can_receive = (
        row.status in {"APPROVED", "SENT", "PARTIALLY_RECEIVED"} and outstanding_lines > 0
    )
    can_close = (
        row.status in {"APPROVED", "SENT", "PARTIALLY_RECEIVED", "FULLY_RECEIVED"}
        and bool(purchase_order_lines)
        and outstanding_lines == 0
    )
    return InventoryDetailViewModel(
        id=row.id,
        title=row.po_number,
        status_label=row.status_label,
        subtitle=f"Supplier: {row.supplier_label}",
        description=row.notes or "No supplier note recorded.",
        fields=(
            InventoryDetailFieldViewModel(
                label="Site",
                value=row.site_label,
            ),
            InventoryDetailFieldViewModel(
                label="Currency / Supplier Ref",
                value=f"{row.currency_code or '-'} / {row.supplier_reference or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Order / Expected Delivery",
                value=f"{row.order_date_label or '-'} / {row.expected_delivery_date_label or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Source Requisition",
                value=row.source_requisition_label or "-",
            ),
            InventoryDetailFieldViewModel(
                label="Workflow Milestones",
                value=(
                    f"Submitted {row.submitted_at_label or '-'} | "
                    f"Approved {row.approved_at_label or '-'} | "
                    f"Sent {row.sent_at_label or '-'} | "
                    f"Cancelled {row.cancelled_at_label or '-'}"
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
        ),
        state={
            "purchaseOrderId": row.id,
            "siteId": row.site_id,
            "supplierPartyId": row.supplier_party_id,
            "sourceRequisitionId": row.source_requisition_id or "",
            "currencyCode": row.currency_code,
            "supplierReference": row.supplier_reference,
            "expectedDeliveryDateIso": row.expected_delivery_date.isoformat()
            if row.expected_delivery_date is not None
            else "",
            "notes": row.notes,
            "status": row.status,
            "version": row.version,
            "hasLines": bool(purchase_order_lines),
            "canEdit": is_draft,
            "canAddLine": is_draft,
            "canSubmit": is_draft and bool(purchase_order_lines),
            "canCancel": is_draft,
            "canSend": row.status == "APPROVED",
            "canPostReceipt": can_receive,
            "canClose": can_close,
        },
    )
