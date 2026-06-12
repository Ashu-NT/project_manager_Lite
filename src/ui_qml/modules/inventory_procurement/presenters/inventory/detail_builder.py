from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
)

from .state_mapper import build_balance_state, build_storeroom_state


def build_storeroom_detail(storeroom) -> InventoryDetailViewModel:
    if storeroom is None:
        return InventoryDetailViewModel(
            title="No storeroom selected",
            empty_state="Select a storeroom to review governance settings, manager ownership, and operational flags.",
        )
    capabilities = ", ".join(
        bit
        for bit in (
            "Issue" if storeroom.allows_issue else "",
            "Transfer" if storeroom.allows_transfer else "",
            "Receiving" if storeroom.allows_receiving else "",
        )
        if bit
    ) or "No operational permissions"
    policy_bits = ", ".join(
        bit
        for bit in (
            "Reservation required" if storeroom.requires_reservation_for_issue else "",
            "Supplier reference required"
            if storeroom.requires_supplier_reference_for_receipt
            else "",
        )
        if bit
    ) or "No extra policy flags"
    return InventoryDetailViewModel(
        id=storeroom.id,
        title=f"{storeroom.storeroom_code} - {storeroom.name}",
        status_label=storeroom.status_label,
        subtitle=storeroom.site_label,
        description=storeroom.description or "No storeroom description has been added yet.",
        fields=(
            InventoryDetailFieldViewModel(label="Active", value=storeroom.active_label),
            InventoryDetailFieldViewModel(
                label="Storeroom type",
                value=storeroom.storeroom_type or "-",
            ),
            InventoryDetailFieldViewModel(
                label="Capabilities",
                value=capabilities,
                supporting_text=policy_bits,
            ),
            InventoryDetailFieldViewModel(
                label="Manager party",
                value=storeroom.manager_party_label or "No manager party",
            ),
            InventoryDetailFieldViewModel(
                label="Default currency",
                value=storeroom.default_currency_code or "-",
            ),
            InventoryDetailFieldViewModel(
                label="Version",
                value=str(storeroom.version),
            ),
        ),
        state=build_storeroom_state(storeroom),
    )


def build_balance_detail(balance) -> InventoryDetailViewModel:
    if balance is None:
        return InventoryDetailViewModel(
            title="No balance selected",
            empty_state="Select a balance row to inspect stock position or launch movement actions.",
        )
    return InventoryDetailViewModel(
        id=balance.id,
        title=balance.stock_item_label,
        status_label="Reorder" if balance.reorder_required else "Healthy",
        subtitle=balance.storeroom_label,
        description=(
            f"On hand {balance.on_hand_qty_label}, available {balance.available_qty_label}, reserved {balance.reserved_qty_label}."
        ),
        fields=(
            InventoryDetailFieldViewModel(
                label="On hand",
                value=balance.on_hand_qty_label,
                supporting_text=f"Reserved {balance.reserved_qty_label} | Committed {balance.committed_qty_label}",
            ),
            InventoryDetailFieldViewModel(
                label="Available / On order",
                value=f"{balance.available_qty_label} available",
                supporting_text=f"{balance.on_order_qty_label} on order",
            ),
            InventoryDetailFieldViewModel(
                label="Average cost",
                value=balance.average_cost_label,
                supporting_text=f"UOM {balance.uom or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Receipts / Issues",
                value=f"Last receipt {balance.last_receipt_at_label or '-'}",
                supporting_text=f"Last issue {balance.last_issue_at_label or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Version",
                value=str(balance.version),
            ),
        ),
        state=build_balance_state(balance),
    )
