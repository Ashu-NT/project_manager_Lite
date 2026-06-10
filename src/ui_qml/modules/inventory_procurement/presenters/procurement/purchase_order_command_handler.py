from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryPurchaseOrderCreateCommand,
    InventoryPurchaseOrderLineCreateCommand,
    InventoryPurchaseOrderUpdateCommand,
)

from .validation import (
    optional_date,
    optional_float,
    optional_int,
    optional_text,
    require_identifier,
    require_positive_float,
    require_text,
)


def create_purchase_order(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.create_purchase_order(
        InventoryPurchaseOrderCreateCommand(
            site_id=require_text(
                payload,
                "siteId",
                "Choose a site before saving the purchase order.",
            ),
            supplier_party_id=require_text(
                payload,
                "supplierPartyId",
                "Choose a supplier before saving the purchase order.",
            ),
            currency_code=optional_text(payload, "currencyCode"),
            source_requisition_id=optional_text(payload, "sourceRequisitionId"),
            expected_delivery_date=optional_date(payload, "expectedDeliveryDate"),
            supplier_reference=optional_text(payload, "supplierReference") or "",
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_purchase_order(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.update_purchase_order(
        InventoryPurchaseOrderUpdateCommand(
            purchase_order_id=require_text(
                payload,
                "purchaseOrderId",
                "Select a purchase order before editing it.",
            ),
            site_id=require_text(
                payload,
                "siteId",
                "Choose a site before saving the purchase order.",
            ),
            supplier_party_id=require_text(
                payload,
                "supplierPartyId",
                "Choose a supplier before saving the purchase order.",
            ),
            currency_code=optional_text(payload, "currencyCode"),
            source_requisition_id=optional_text(payload, "sourceRequisitionId"),
            expected_delivery_date=optional_date(payload, "expectedDeliveryDate"),
            supplier_reference=optional_text(payload, "supplierReference") or "",
            notes=optional_text(payload, "notes") or "",
            expected_version=optional_int(payload, "expectedVersion"),
        )
    )


def add_purchase_order_line(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.add_purchase_order_line(
        InventoryPurchaseOrderLineCreateCommand(
            purchase_order_id=require_text(
                payload,
                "purchaseOrderId",
                "Select a purchase order before adding a line.",
            ),
            stock_item_id=require_text(
                payload,
                "stockItemId",
                "Choose an item before adding a purchase-order line.",
            ),
            destination_storeroom_id=require_text(
                payload,
                "destinationStoreroomId",
                "Choose a destination storeroom before adding a line.",
            ),
            quantity_ordered=require_positive_float(
                payload,
                "quantityOrdered",
                "Ordered quantity must be greater than zero.",
            ),
            unit_price=optional_float(payload, "unitPrice") or 0.0,
            expected_delivery_date=optional_date(payload, "expectedDeliveryDate"),
            description=optional_text(payload, "description") or "",
            source_requisition_line_id=optional_text(payload, "sourceRequisitionLineId"),
            notes=optional_text(payload, "notes") or "",
        )
    )


def submit_purchase_order(desktop_api, purchase_order_id: str) -> None:
    desktop_api.submit_purchase_order(
        require_identifier(purchase_order_id, "Select a purchase order before submitting it.")
    )


def send_purchase_order(desktop_api, purchase_order_id: str) -> None:
    desktop_api.send_purchase_order(
        require_identifier(purchase_order_id, "Select a purchase order before sending it.")
    )


def cancel_purchase_order(desktop_api, purchase_order_id: str) -> None:
    desktop_api.cancel_purchase_order(
        require_identifier(purchase_order_id, "Select a purchase order before cancelling it.")
    )


def close_purchase_order(desktop_api, purchase_order_id: str) -> None:
    desktop_api.close_purchase_order(
        require_identifier(purchase_order_id, "Select a purchase order before closing it.")
    )
