from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)


def to_requisition_record_view_model(row) -> InventoryRecordViewModel:
    return InventoryRecordViewModel(
        id=row.id,
        title=row.requisition_number,
        status_label=row.status_label,
        subtitle=f"{row.requesting_site_label} | {row.requesting_storeroom_label}",
        supporting_text=(
            f"Priority {row.priority or '-'} | Needed {row.needed_by_date_label or '-'}"
        ),
        meta_text=(
            f"Requester {row.requester_username or '-'} | {row.purpose or 'No purpose'}"
        ),
        state={
            "requisitionId": row.id,
            "requestingSiteId": row.requesting_site_id,
            "requestingStoreroomId": row.requesting_storeroom_id,
            "priority": row.priority,
            "status": row.status,
            "version": row.version,
        },
    )


def build_requisition_line_options(
    desktop_api,
    requisition_id: str | None,
) -> tuple[InventorySelectorOptionViewModel, ...]:
    normalized_id = (requisition_id or "").strip()
    if not normalized_id:
        return ()
    options: list[InventorySelectorOptionViewModel] = []
    for line in desktop_api.list_requisition_lines(normalized_id):
        remaining = max(
            0.0,
            float(line.quantity_requested or 0.0) - float(line.quantity_sourced or 0.0),
        )
        if remaining <= 0:
            continue
        options.append(
            InventorySelectorOptionViewModel(
                value=line.id,
                label=(
                    f"L{line.line_number} | {line.stock_item_label} | "
                    f"Remaining {remaining:,.3f}"
                ),
            )
        )
    return tuple(options)
