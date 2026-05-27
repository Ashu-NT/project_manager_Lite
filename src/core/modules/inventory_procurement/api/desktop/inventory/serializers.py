from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_amount,
    format_bool_label,
    format_date,
    format_datetime,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryCycleCountDesktopDto,
    InventoryFoundationSignalDesktopDto,
    InventoryReorderPolicyDesktopDto,
    InventoryStockBalanceDesktopDto,
    InventoryStockTransactionDesktopDto,
    InventoryStorageLocationDesktopDto,
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


def serialize_storage_location(
    row,
    *,
    storeroom_lookup: dict[str, str],
    parent_lookup: dict[str, str],
) -> InventoryStorageLocationDesktopDto:
    location_type = getattr(getattr(row, "location_type", None), "value", getattr(row, "location_type", ""))
    location_id = clean_text(getattr(row, "id", ""))
    parent_location_id = clean_text(getattr(row, "parent_location_id", "")) or None
    is_active = bool(getattr(row, "is_active", True))
    is_quarantine = bool(getattr(row, "is_quarantine", False))
    return InventoryStorageLocationDesktopDto(
        id=location_id,
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        location_code=clean_text(getattr(row, "location_code", "")),
        name=clean_text(getattr(row, "name", "")),
        parent_location_id=parent_location_id,
        parent_location_label=parent_lookup.get(parent_location_id or "", "-"),
        location_type=str(location_type or ""),
        location_type_label=format_enum_label(str(location_type or "")),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        is_quarantine=is_quarantine,
        quarantine_label="Quarantine" if is_quarantine else "Standard",
        allows_issue=bool(getattr(row, "allows_issue", True)),
        allows_putaway=bool(getattr(row, "allows_putaway", True)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_reorder_policy(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
    location_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> InventoryReorderPolicyDesktopDto:
    is_active = bool(getattr(row, "is_active", True))
    location_id = clean_text(getattr(row, "location_id", "")) or None
    preferred_supplier_party_id = clean_text(getattr(row, "preferred_supplier_party_id", "")) or None
    return InventoryReorderPolicyDesktopDto(
        id=clean_text(getattr(row, "id", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        location_id=location_id,
        location_label=location_lookup.get(location_id or "", "-"),
        policy_name=clean_text(getattr(row, "policy_name", "")),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        min_qty=float(getattr(row, "min_qty", 0.0) or 0.0),
        min_qty_label=format_quantity(getattr(row, "min_qty", 0.0)),
        max_qty=float(getattr(row, "max_qty", 0.0) or 0.0),
        max_qty_label=format_quantity(getattr(row, "max_qty", 0.0)),
        reorder_point=float(getattr(row, "reorder_point", 0.0) or 0.0),
        reorder_point_label=format_quantity(getattr(row, "reorder_point", 0.0)),
        reorder_qty=float(getattr(row, "reorder_qty", 0.0) or 0.0),
        reorder_qty_label=format_quantity(getattr(row, "reorder_qty", 0.0)),
        economic_order_qty=float(getattr(row, "economic_order_qty", 0.0) or 0.0),
        economic_order_qty_label=format_quantity(
            getattr(row, "economic_order_qty", 0.0)
        ),
        lead_time_days=getattr(row, "lead_time_days", None),
        lead_time_days_label=clean_text(getattr(row, "lead_time_days", None), default="-"),
        review_period_days=getattr(row, "review_period_days", None),
        review_period_days_label=clean_text(getattr(row, "review_period_days", None), default="-"),
        preferred_supplier_party_id=preferred_supplier_party_id,
        preferred_supplier_label=party_lookup.get(preferred_supplier_party_id or "", "-"),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_cycle_count(
    row,
    *,
    item_lookup: dict[str, str],
    storeroom_lookup: dict[str, str],
    location_lookup: dict[str, str],
) -> InventoryCycleCountDesktopDto:
    status = getattr(getattr(row, "status", None), "value", getattr(row, "status", ""))
    location_id = clean_text(getattr(row, "location_id", "")) or None
    counted_qty = getattr(row, "counted_qty", None)
    return InventoryCycleCountDesktopDto(
        id=clean_text(getattr(row, "id", "")),
        cycle_count_number=clean_text(getattr(row, "cycle_count_number", "")),
        stock_item_id=clean_text(getattr(row, "stock_item_id", "")),
        stock_item_label=item_lookup.get(clean_text(getattr(row, "stock_item_id", "")), "-"),
        storeroom_id=clean_text(getattr(row, "storeroom_id", "")),
        storeroom_label=storeroom_lookup.get(clean_text(getattr(row, "storeroom_id", "")), "-"),
        location_id=location_id,
        location_label=location_lookup.get(location_id or "", "-"),
        scheduled_count_date_label=format_date(getattr(row, "scheduled_count_date", None)),
        status=str(status or ""),
        status_label=format_enum_label(str(status or "")),
        expected_qty=float(getattr(row, "expected_qty", 0.0) or 0.0),
        expected_qty_label=format_quantity(getattr(row, "expected_qty", 0.0)),
        counted_qty=None if counted_qty is None else float(counted_qty),
        counted_qty_label="-" if counted_qty is None else format_quantity(counted_qty),
        variance_qty=float(getattr(row, "variance_qty", 0.0) or 0.0),
        variance_qty_label=format_quantity(getattr(row, "variance_qty", 0.0)),
        counted_by_username=clean_text(getattr(row, "counted_by_username", ""), default="-"),
        completed_at_label=format_datetime(getattr(row, "completed_at", None)),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_foundation_signal(
    *,
    signal_id: str,
    title: str,
    subtitle: str,
    status_label: str,
    supporting_text: str,
    meta_text: str,
    tone: str = "default",
) -> InventoryFoundationSignalDesktopDto:
    return InventoryFoundationSignalDesktopDto(
        id=clean_text(signal_id),
        title=clean_text(title, default="-"),
        subtitle=clean_text(subtitle, default="-"),
        status_label=clean_text(status_label, default="-"),
        supporting_text=clean_text(supporting_text, default="-"),
        meta_text=clean_text(meta_text, default="-"),
        tone=clean_text(tone, default="default"),
    )


__all__ = [
    "serialize_cycle_count",
    "serialize_foundation_signal",
    "serialize_reorder_policy",
    "serialize_balance",
    "serialize_storage_location",
    "serialize_storeroom",
    "serialize_transaction",
]
