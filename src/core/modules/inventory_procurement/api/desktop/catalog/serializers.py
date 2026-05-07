from __future__ import annotations

from src.core.modules.inventory_procurement.api.desktop._support import (
    clean_text,
    format_bool_label,
    format_date,
    format_enum_label,
    format_quantity,
)
from src.core.modules.inventory_procurement.api.desktop.catalog.models import (
    InventoryCategoryDesktopDto,
    InventoryDocumentOptionDescriptor,
    InventoryItemDesktopDto,
)


def serialize_document(row) -> InventoryDocumentOptionDescriptor:
    document_type = getattr(
        getattr(row, "document_type", None),
        "value",
        getattr(row, "document_type", ""),
    )
    storage_kind = getattr(
        getattr(row, "storage_kind", None),
        "value",
        getattr(row, "storage_kind", ""),
    )
    label = " - ".join(
        part
        for part in (
            clean_text(getattr(row, "document_code", "")),
            clean_text(getattr(row, "title", "")),
        )
        if part
    )
    return InventoryDocumentOptionDescriptor(
        value=row.id,
        label=label or clean_text(getattr(row, "title", ""), default="-"),
        document_type=str(document_type or ""),
        storage_kind=str(storage_kind or ""),
        effective_date_label=format_date(getattr(row, "effective_date", None)),
        is_active=bool(getattr(row, "is_active", True)),
    )


def serialize_category(row) -> InventoryCategoryDesktopDto:
    category_type = clean_text(getattr(row, "category_type", ""))
    is_active = bool(getattr(row, "is_active", True))
    return InventoryCategoryDesktopDto(
        id=row.id,
        category_code=clean_text(getattr(row, "category_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        category_type=category_type,
        category_type_label=format_enum_label(category_type),
        is_equipment=bool(getattr(row, "is_equipment", False)),
        supports_project_usage=bool(getattr(row, "supports_project_usage", False)),
        supports_maintenance_usage=bool(
            getattr(row, "supports_maintenance_usage", False)
        ),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        version=int(getattr(row, "version", 1) or 1),
    )


def serialize_item(
    row,
    *,
    category_lookup: dict[str, str],
    party_lookup: dict[str, str],
) -> InventoryItemDesktopDto:
    status = clean_text(getattr(row, "status", ""))
    category_code = clean_text(getattr(row, "category_code", ""))
    preferred_party_id = clean_text(getattr(row, "preferred_party_id", "")) or None
    is_active = bool(getattr(row, "is_active", False))
    return InventoryItemDesktopDto(
        id=row.id,
        item_code=clean_text(getattr(row, "item_code", "")),
        name=clean_text(getattr(row, "name", "")),
        description=clean_text(getattr(row, "description", "")),
        item_type=clean_text(getattr(row, "item_type", "")),
        status=status,
        status_label=format_enum_label(status),
        stock_uom=clean_text(getattr(row, "stock_uom", "")),
        order_uom=clean_text(getattr(row, "order_uom", "")),
        issue_uom=clean_text(getattr(row, "issue_uom", "")),
        order_uom_ratio=float(getattr(row, "order_uom_ratio", 1.0) or 1.0),
        order_uom_ratio_label=format_quantity(
            getattr(row, "order_uom_ratio", 1.0),
            decimals=3,
        ),
        issue_uom_ratio=float(getattr(row, "issue_uom_ratio", 1.0) or 1.0),
        issue_uom_ratio_label=format_quantity(
            getattr(row, "issue_uom_ratio", 1.0),
            decimals=3,
        ),
        category_code=category_code,
        category_label=category_lookup.get(category_code, "-"),
        commodity_code=clean_text(getattr(row, "commodity_code", "")),
        is_stocked=bool(getattr(row, "is_stocked", True)),
        is_purchase_allowed=bool(getattr(row, "is_purchase_allowed", True)),
        is_active=is_active,
        active_label=format_bool_label(is_active),
        default_reorder_policy=clean_text(
            getattr(row, "default_reorder_policy", "")
        ),
        min_qty=float(getattr(row, "min_qty", 0.0) or 0.0),
        min_qty_label=format_quantity(getattr(row, "min_qty", 0.0)),
        max_qty=float(getattr(row, "max_qty", 0.0) or 0.0),
        max_qty_label=format_quantity(getattr(row, "max_qty", 0.0)),
        reorder_point=float(getattr(row, "reorder_point", 0.0) or 0.0),
        reorder_point_label=format_quantity(getattr(row, "reorder_point", 0.0)),
        reorder_qty=float(getattr(row, "reorder_qty", 0.0) or 0.0),
        reorder_qty_label=format_quantity(getattr(row, "reorder_qty", 0.0)),
        lead_time_days=getattr(row, "lead_time_days", None),
        shelf_life_days=getattr(row, "shelf_life_days", None),
        is_lot_tracked=bool(getattr(row, "is_lot_tracked", False)),
        is_serial_tracked=bool(getattr(row, "is_serial_tracked", False)),
        preferred_party_id=preferred_party_id,
        preferred_party_label=party_lookup.get(preferred_party_id or "", "-"),
        notes=clean_text(getattr(row, "notes", "")),
        version=int(getattr(row, "version", 1) or 1),
    )


__all__ = [
    "serialize_category",
    "serialize_document",
    "serialize_item",
]
