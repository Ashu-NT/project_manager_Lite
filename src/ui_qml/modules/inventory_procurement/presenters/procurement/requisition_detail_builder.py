from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
)

from .formatting import format_source_reference


def build_requisition_detail(row, requisition_lines) -> InventoryDetailViewModel:
    if row is None:
        return InventoryDetailViewModel(
            title="No requisition selected",
            empty_state=(
                "Select a requisition to review demand details, add lines, or "
                "move it into procurement approval."
            ),
        )
    is_draft = row.status == "DRAFT"
    return InventoryDetailViewModel(
        id=row.id,
        title=row.requisition_number,
        status_label=row.status_label,
        subtitle=f"Requester: {row.requester_username or '-'}",
        description=row.purpose or "No purpose recorded.",
        fields=(
            InventoryDetailFieldViewModel(
                label="Site",
                value=row.requesting_site_label,
            ),
            InventoryDetailFieldViewModel(
                label="Storeroom",
                value=row.requesting_storeroom_label,
            ),
            InventoryDetailFieldViewModel(
                label="Priority / Needed By",
                value=f"{row.priority or '-'} / {row.needed_by_date_label or '-'}",
            ),
            InventoryDetailFieldViewModel(
                label="Source Reference",
                value=format_source_reference(
                    row.source_reference_type,
                    row.source_reference_id,
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Workflow Milestones",
                value=(
                    f"Submitted {row.submitted_at_label or '-'} | "
                    f"Approved {row.approved_at_label or '-'} | "
                    f"Cancelled {row.cancelled_at_label or '-'}"
                ),
            ),
            InventoryDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
        ),
        state={
            "requisitionId": row.id,
            "requestingSiteId": row.requesting_site_id,
            "requestingStoreroomId": row.requesting_storeroom_id,
            "purpose": row.purpose,
            "priority": row.priority,
            "neededByDateIso": row.needed_by_date.isoformat()
            if row.needed_by_date is not None
            else "",
            "notes": row.notes,
            "status": row.status,
            "version": row.version,
            "hasLines": bool(requisition_lines),
            "canEdit": is_draft,
            "canAddLine": is_draft,
            "canSubmit": is_draft and bool(requisition_lines),
            "canCancel": is_draft,
        },
    )
