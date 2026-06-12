from __future__ import annotations


def build_storeroom_state(storeroom) -> dict[str, object]:
    return {
        "storeroomId": storeroom.id,
        "storeroomCode": storeroom.storeroom_code,
        "name": storeroom.name,
        "description": storeroom.description,
        "siteId": storeroom.site_id,
        "siteLabel": storeroom.site_label,
        "status": storeroom.status,
        "statusLabel": storeroom.status_label,
        "storeroomType": storeroom.storeroom_type,
        "isActive": storeroom.is_active,
        "activeLabel": storeroom.active_label,
        "isInternalSupplier": storeroom.is_internal_supplier,
        "allowsIssue": storeroom.allows_issue,
        "allowsTransfer": storeroom.allows_transfer,
        "allowsReceiving": storeroom.allows_receiving,
        "requiresReservationForIssue": storeroom.requires_reservation_for_issue,
        "requiresSupplierReferenceForReceipt": storeroom.requires_supplier_reference_for_receipt,
        "defaultCurrencyCode": storeroom.default_currency_code or "",
        "managerPartyId": storeroom.manager_party_id or "",
        "managerPartyLabel": storeroom.manager_party_label or "",
        "notes": storeroom.notes,
        "version": storeroom.version,
    }


def build_balance_state(balance) -> dict[str, object]:
    return {
        "balanceId": balance.id,
        "stockItemId": balance.stock_item_id,
        "stockItemLabel": balance.stock_item_label,
        "storeroomId": balance.storeroom_id,
        "storeroomLabel": balance.storeroom_label,
        "uom": balance.uom,
        "averageCost": f"{float(balance.average_cost or 0.0):.2f}",
        "averageCostLabel": balance.average_cost_label,
        "onHandQty": balance.on_hand_qty,
        "onHandQtyLabel": balance.on_hand_qty_label,
        "availableQty": balance.available_qty,
        "availableQtyLabel": balance.available_qty_label,
        "reservedQty": balance.reserved_qty,
        "reservedQtyLabel": balance.reserved_qty_label,
        "committedQty": balance.committed_qty,
        "committedQtyLabel": balance.committed_qty_label,
        "version": balance.version,
    }
