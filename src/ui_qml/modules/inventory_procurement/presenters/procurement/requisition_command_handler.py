from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryRequisitionCreateCommand,
    InventoryRequisitionLineCreateCommand,
    InventoryRequisitionUpdateCommand,
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


def create_requisition(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.create_requisition(
        InventoryRequisitionCreateCommand(
            requesting_site_id=require_text(
                payload,
                "requestingSiteId",
                "Choose a site before saving the requisition.",
            ),
            requesting_storeroom_id=require_text(
                payload,
                "requestingStoreroomId",
                "Choose a storeroom before saving the requisition.",
            ),
            purpose=optional_text(payload, "purpose") or "",
            needed_by_date=optional_date(payload, "neededByDate"),
            priority=optional_text(payload, "priority") or "NORMAL",
            notes=optional_text(payload, "notes") or "",
        )
    )


def update_requisition(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.update_requisition(
        InventoryRequisitionUpdateCommand(
            requisition_id=require_text(
                payload,
                "requisitionId",
                "Select a requisition before editing it.",
            ),
            requesting_site_id=require_text(
                payload,
                "requestingSiteId",
                "Choose a site before saving the requisition.",
            ),
            requesting_storeroom_id=require_text(
                payload,
                "requestingStoreroomId",
                "Choose a storeroom before saving the requisition.",
            ),
            purpose=optional_text(payload, "purpose") or "",
            needed_by_date=optional_date(payload, "neededByDate"),
            priority=optional_text(payload, "priority") or "NORMAL",
            notes=optional_text(payload, "notes") or "",
            expected_version=optional_int(payload, "expectedVersion"),
        )
    )


def add_requisition_line(desktop_api, payload: dict[str, Any]) -> None:
    desktop_api.add_requisition_line(
        InventoryRequisitionLineCreateCommand(
            requisition_id=require_text(
                payload,
                "requisitionId",
                "Select a requisition before adding a line.",
            ),
            stock_item_id=require_text(
                payload,
                "stockItemId",
                "Choose an item before adding a requisition line.",
            ),
            quantity_requested=require_positive_float(
                payload,
                "quantityRequested",
                "Requested quantity must be greater than zero.",
            ),
            description=optional_text(payload, "description") or "",
            needed_by_date=optional_date(payload, "neededByDate"),
            estimated_unit_cost=optional_float(payload, "estimatedUnitCost") or 0.0,
            suggested_supplier_party_id=optional_text(payload, "suggestedSupplierPartyId"),
            notes=optional_text(payload, "notes") or "",
        )
    )


def submit_requisition(desktop_api, requisition_id: str) -> None:
    desktop_api.submit_requisition(
        require_identifier(requisition_id, "Select a requisition before submitting it.")
    )


def cancel_requisition(desktop_api, requisition_id: str) -> None:
    desktop_api.cancel_requisition(
        require_identifier(requisition_id, "Select a requisition before cancelling it.")
    )
