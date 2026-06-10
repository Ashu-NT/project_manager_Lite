from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryDocumentOptionViewModel,
)

from .state_mapper import build_category_state, build_item_state


def build_category_detail(category) -> InventoryDetailViewModel:
    if category is None:
        return InventoryDetailViewModel(
            title="No category selected",
            empty_state="Select a category from the catalog to review usage flags or update its governance settings.",
        )
    state = build_category_state(category)
    usage_bits = []
    if category.is_equipment:
        usage_bits.append("Equipment")
    if category.supports_project_usage:
        usage_bits.append("Projects")
    if category.supports_maintenance_usage:
        usage_bits.append("Maintenance")
    return InventoryDetailViewModel(
        id=category.id,
        title=f"{category.category_code} - {category.name}",
        status_label=category.active_label,
        subtitle=", ".join(usage_bits) or "Inventory only",
        description=category.description or "No category description has been added yet.",
        fields=(
            InventoryDetailFieldViewModel(
                label="Category type",
                value=category.category_type_label,
            ),
            InventoryDetailFieldViewModel(
                label="Usage",
                value=", ".join(usage_bits) or "Inventory only",
            ),
            InventoryDetailFieldViewModel(
                label="Active",
                value=category.active_label,
            ),
            InventoryDetailFieldViewModel(
                label="Version",
                value=str(category.version),
            ),
        ),
        state=state,
    )


def build_item_detail(item, desktop_api) -> InventoryDetailViewModel:
    if item is None:
        return InventoryDetailViewModel(
            title="No item selected",
            empty_state="Select an item from the catalog to review operational fields, supplier context, and linked documents.",
        )
    linked_documents = tuple(
        InventoryDocumentOptionViewModel(
            value=document.value,
            label=document.label,
            document_type=document.document_type,
            storage_kind=document.storage_kind,
            effective_date_label=document.effective_date_label,
            is_active=document.is_active,
        )
        for document in desktop_api.list_linked_documents(item.id, active_only=None)
    )
    state = build_item_state(item)
    return InventoryDetailViewModel(
        id=item.id,
        title=f"{item.item_code} - {item.name}",
        status_label=item.active_label,
        subtitle=item.preferred_party_label if item.preferred_party_id else "No preferred supplier",
        description=item.description or "No item description has been added yet.",
        fields=(
            InventoryDetailFieldViewModel(
                label="Status",
                value=item.status_label,
            ),
            InventoryDetailFieldViewModel(
                label="Category",
                value=item.category_label or "Uncategorized",
            ),
            InventoryDetailFieldViewModel(
                label="UOM",
                value=item.stock_uom or "-",
                supporting_text=(
                    f"Order {item.order_uom or item.stock_uom or '-'} "
                    f"({item.order_uom_ratio_label}) | "
                    f"Issue {item.issue_uom or item.stock_uom or '-'} "
                    f"({item.issue_uom_ratio_label})"
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Replenishment",
                value=(
                    f"Min {item.min_qty_label} | Max {item.max_qty_label} | "
                    f"ROP {item.reorder_point_label} | ROQ {item.reorder_qty_label}"
                ),
                supporting_text=(
                    f"Lead time: {item.lead_time_days if item.lead_time_days is not None else '-'} days"
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Tracking",
                value=", ".join(
                    bit
                    for bit in (
                        "Stocked" if item.is_stocked else "",
                        "Purchasable" if item.is_purchase_allowed else "",
                        "Lot tracked" if item.is_lot_tracked else "",
                        "Serial tracked" if item.is_serial_tracked else "",
                    )
                    if bit
                )
                or "No special tracking flags",
                supporting_text=(
                    f"Shelf life: {item.shelf_life_days if item.shelf_life_days is not None else '-'} days"
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Preferred party",
                value=item.preferred_party_label or "No preferred party",
            ),
            InventoryDetailFieldViewModel(
                label="Version",
                value=str(item.version),
            ),
        ),
        linked_documents=linked_documents,
        state=state,
    )
