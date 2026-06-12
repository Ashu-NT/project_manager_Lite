from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.foundation import (
    InventoryInventoryFoundationViewModel,
    InventoryModuleLinkViewModel,
)

from .signal_mapper import to_foundation_signal_record


def build_foundation(
    desktop_api,
    *,
    site_filter: str,
    storeroom_scope: str | None,
    item_filter: str,
) -> InventoryInventoryFoundationViewModel:
    snapshot = desktop_api.build_foundation_snapshot(
        site_id=None if site_filter == "all" else site_filter,
        storeroom_id=storeroom_scope or None,
        stock_item_id=None if item_filter == "all" else item_filter,
        limit=12,
    )
    return InventoryInventoryFoundationViewModel(
        title=snapshot.title,
        subtitle=snapshot.subtitle,
        metrics=tuple(
            InventoryCatalogMetricViewModel(
                label=metric.label,
                value=metric.value,
                supporting_text=metric.supporting_text,
            )
            for metric in snapshot.metrics
        ),
        module_links=tuple(
            InventoryModuleLinkViewModel(
                code=entry.code,
                label=entry.label,
                kind=entry.kind,
                is_enabled=entry.is_enabled,
                status_label=entry.status_label,
                reason=entry.reason,
                route_id=entry.route_id,
            )
            for entry in snapshot.module_links
        ),
        location_type_options=tuple(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_location_types()
        ),
        cycle_count_status_options=tuple(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_cycle_count_statuses()
        ),
        locations=tuple(
            InventoryRecordViewModel(
                id=row.id,
                title=f"{row.location_code} - {row.name}",
                status_label=row.location_type_label,
                subtitle=row.storeroom_label,
                supporting_text=" | ".join(
                    bit
                    for bit in (
                        row.parent_location_label
                        if row.parent_location_id
                        else "Top-level location",
                        row.quarantine_label,
                        "Issue enabled" if row.allows_issue else "No issue",
                        "Putaway enabled" if row.allows_putaway else "No putaway",
                    )
                    if bit
                ),
                meta_text=row.active_label,
                state={
                    "locationId": row.id,
                    "storeroomId": row.storeroom_id,
                    "parentLocationId": row.parent_location_id or "",
                    "locationType": row.location_type,
                    "isActive": row.is_active,
                    "version": row.version,
                },
            )
            for row in snapshot.locations
        ),
        reorder_policies=tuple(
            InventoryRecordViewModel(
                id=row.id,
                title=row.stock_item_label,
                status_label=row.active_label,
                subtitle=row.storeroom_label,
                supporting_text=(
                    f"RP {row.reorder_point_label} | RQ {row.reorder_qty_label} | "
                    f"Min {row.min_qty_label} | Max {row.max_qty_label}"
                ),
                meta_text=(
                    row.location_label
                    if row.location_id
                    else row.preferred_supplier_label or "Global storeroom policy"
                ),
                state={
                    "policyId": row.id,
                    "stockItemId": row.stock_item_id,
                    "storeroomId": row.storeroom_id,
                    "locationId": row.location_id or "",
                    "version": row.version,
                },
            )
            for row in snapshot.reorder_policies
        ),
        cycle_counts=tuple(
            InventoryRecordViewModel(
                id=row.id,
                title=row.cycle_count_number,
                status_label=row.status_label,
                subtitle=row.stock_item_label,
                supporting_text=(
                    f"Expected {row.expected_qty_label} | Counted {row.counted_qty_label} | "
                    f"Variance {row.variance_qty_label}"
                ),
                meta_text=" | ".join(
                    bit
                    for bit in (
                        row.storeroom_label,
                        row.location_label if row.location_id else "",
                        row.scheduled_count_date_label,
                    )
                    if bit and bit != "-"
                ),
                state={
                    "cycleCountId": row.id,
                    "stockItemId": row.stock_item_id,
                    "storeroomId": row.storeroom_id,
                    "locationId": row.location_id or "",
                    "status": row.status,
                    "version": row.version,
                },
            )
            for row in snapshot.cycle_counts
        ),
        valuation_signals=tuple(
            to_foundation_signal_record(row) for row in snapshot.valuation_signals
        ),
        tracking_signals=tuple(
            to_foundation_signal_record(row) for row in snapshot.tracking_signals
        ),
        activity_signals=tuple(
            to_foundation_signal_record(row) for row in snapshot.activity_signals
        ),
    )
