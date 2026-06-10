from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.register import (
    RegisterRecordViewModel,
)

from .formatting import preview_text
from .utils import WorkspaceMode


def build_entry_state(entry) -> dict[str, object]:
    return {
        "entryId": entry.id,
        "projectId": entry.project_id,
        "projectName": entry.project_name,
        "entryCode": getattr(entry, "code", "") or "",
        "type": entry.entry_type,
        "typeLabel": entry.entry_type_label,
        "title": entry.title,
        "description": entry.description or "",
        "severity": entry.severity,
        "severityLabel": entry.severity_label,
        "status": entry.status,
        "statusLabel": entry.status_label,
        "ownerName": entry.owner_name or "",
        "dueDate": entry.due_date.isoformat() if entry.due_date else "",
        "dueDateLabel": entry.due_date_label,
        "impactSummary": entry.impact_summary or "",
        "responsePlan": entry.response_plan or "",
        "isOverdue": entry.is_overdue,
        "version": entry.version,
    }


def to_record_view_model(entry, *, workspace_mode: WorkspaceMode) -> RegisterRecordViewModel:
    state = build_entry_state(entry)
    subtitle_parts = [
        state["typeLabel"],
        state["statusLabel"],
        state["ownerName"] or "Unassigned",
    ]
    supporting_parts = [
        f"Project: {state['projectName']}",
        f"Due: {state['dueDateLabel']}",
    ]
    if workspace_mode == "risk":
        subtitle_parts = [
            state["statusLabel"],
            state["ownerName"] or "Unassigned",
        ]
    return RegisterRecordViewModel(
        id=entry.id,
        title=entry.title,
        status_label=entry.severity_label,
        subtitle=" | ".join(part for part in subtitle_parts if part),
        supporting_text=" | ".join(part for part in supporting_parts if part),
        meta_text=preview_text(
            entry.response_plan,
            entry.impact_summary,
            entry.description,
        ),
        state=state,
    )
