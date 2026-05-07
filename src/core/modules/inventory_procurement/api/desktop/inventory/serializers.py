from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_bool_label,
    format_datetime,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryStockBalanceDesktopDto,
    InventoryStockTransactionDesktopDto,
    InventoryStoreroomDesktopDto,
)


def serialize_storeroom(
    row,
    *,
    site_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> InventoryStoreroomDesktopDto:
    status = clean_text(getattr(row, "status", ""))
    site_id = clean_text(getattr(row, "site_id", ""))
    manager_party_id = clean_text(getattr(row, "manager_party_id", "")) or None
    is_active = bool(getattr(row, "is_active", False))
    return InventoryStoreroomDesktopDto(
        id=row.id,
        storeroom_code=clean_text(getattr(row, "storeroom_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        site_id=site_id,
        site_label=site_lookup.get(site_id, "-"),
        status=status,
        status_label=format_enum_label(status),
        storeroom_type=clean_text(getattr(row, "storeroom_type", "")),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        is_internal_supplier=bool(getattr(row, "is_internal_supplier", False)),
        allows_issue=bool(getattr(row, "allows_issue", True)),
        allows_transfer=bool(getattr(row, "allows_transfer", True)),
        allows_receiving=bool(getattr(row, "allows_receiving", True)),
        requires_reservation_for_issue=bool(
            getattr(row, "requires_reservation_for_issue", False)
        ),
        requires_supplier_reference_for_receipt=bool(
            getattr(row, "requires_supplier_reference_for_receipt", False)
        ),
        default_currency_code=clean_text(getattr(row, "default_currency_code", "")),
        manager_party_id=manager_party_id,
        manager_party_label=party_lookup.get(manager_party_id or "", "-"),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_balance(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryStockBalanceDesktopDto:
    average_cost = float(getattr(row, "average_cost", 0.0) or 0.0)
    return InventoryStockBalanceDesktopDto(
        id=row.id,
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        uom=clean_text(getattr(row, "uom", "")),
        on_hand_qty=float(getattr(row, "on_hand_qty", 0.0) or 0.0),
        on_hand_qty_label=format_quantity(getattr(row, "on_hand_qty", 0.0)),
        reserved_qty=float(getattr(row, "reserved_qty", 0.0) or 0.0),
        reserved_qty_label=format_quantity(getattr(row, "reserved_qty", 0.0)),
        available_qty=float(getattr(row, "available_qty", 0.0) or 0.0),
        available_qty_label=format_quantity(getattr(row, "available_qty", 0.0)),
        on_order_qty=float(getattr(row, "on_order_qty", 0.0) or 0.0),
        on_order_qty_label=format_quantity(getattr(row, "on_order_qty", 0.0)),
        committed_qty=float(getattr(row, "committed_qty", 0.0) or 0.0),
        committed_qty_label=format_quantity(getattr(row, "committed_qty", 0.0)),
        average_cost=average_cost,
        average_cost_label=format_amount(average_cost),
        last_receipt_at_label=format_datetime(getattr(row, "last_receipt_at", None)),
        last_issue_at_label=format_datetime(getattr(row, "last_issue_at", None)),
        reorder_required=bool(getattr(row, "reorder_required", False)),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_transaction(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
) -> InventoryStockTransactionDesktopDto:
    transaction_type = getattr(
        getattr(row, "transaction_type", None),
        "value",
        getattr(row, "transaction_type", ""),
    )
    return InventoryStockTransactionDesktopDto(
        id=row.id,
        transaction_number=clean_text(getattr(row, "transaction_number", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        transaction_type=str(transaction_type or ""),
        transaction_type_label=format_enum_label(str(transaction_type or "")),
        quantity=float(getattr(row, "quantity", 0.0) or 0.0),
        quantity_label=format_quantity(getattr(row, "quantity", 0.0)),
        uom=clean_text(getattr(row, "uom", "")),
        unit_cost=float(getattr(row, "unit_cost", 0.0) or 0.0),
        unit_cost_label=format_amount(getattr(row, "unit_cost", 0.0)),
        transaction_at_label=format_datetime(getattr(row, "transaction_at", None)),
        reference_type=clean_text(getattr(row, "reference_type", "")),
        reference_id=clean_text(getattr(row, "reference_id", "")),
        performed_by_username=clean_text(getattr(row, "performed_by_username", ""), default="-"),
        resulting_on_hand_qty_label=format_quantity(
            getattr(row, "resulting_on_hand_qty", 0.0)
        ),
        resulting_available_qty_label=format_quantity(
            getattr(row, "resulting_available_qty", 0.0)
        ),
        notes=clean_text(getattr(row, "notes", "")),
    )


__all__ = [
    "serialize_balance",
    "serialize_storeroom",
    "serialize_transaction",
]
