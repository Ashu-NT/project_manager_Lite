from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryReceiptLineCommand,
    InventoryReceiptPostCommand,
)

from .validation import (
    optional_float,
    optional_text,
    require_non_negative_float,
    require_text,
)

def post_receipt(desktop_api, payload: dict[str, Any]) -> None:
    purchase_order_id = require_text(
        payload,
        "purchaseOrderId",
        "Select a purchase order before posting a receipt.",
    )
    raw_lines = payload.get("receiptLines", ())
    receipt_lines = tuple(
        InventoryReceiptLineCommand(
            purchase_order_line_id=require_text(
                dict(line),
                "purchaseOrderLineId",
                "Receipt line data is missing a purchase-order line reference.",
            ),
            quantity_accepted=require_non_negative_float(
                dict(line),
                "quantityAccepted",
                "Accepted quantity must be zero or greater.",
            ),
            quantity_rejected=require_non_negative_float(
                dict(line),
                "quantityRejected",
                "Rejected quantity must be zero or greater.",
            ),
            unit_cost=optional_float(dict(line), "unitCost"),
            notes=optional_text(dict(line), "notes") or "",
        )
        for line in raw_lines
    )
    if not receipt_lines:
        raise ValueError(
            "Enter at least one accepted or rejected quantity before posting the receipt."
        )
    if not any(
        line.quantity_accepted > 0 or line.quantity_rejected > 0
        for line in receipt_lines
    ):
        raise ValueError(
            "Enter at least one accepted or rejected quantity before posting the receipt."
        )
    desktop_api.post_receipt(
        InventoryReceiptPostCommand(
            purchase_order_id=purchase_order_id,
            receipt_lines=receipt_lines,
            supplier_delivery_reference=optional_text(payload, "supplierDeliveryReference") or "",
            notes=optional_text(payload, "notes") or "",
        )
    )
