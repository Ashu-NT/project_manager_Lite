from __future__ import annotations


from src.core.modules.project_management.application.risk.dto.responses.entries import RegisterEntryResponseDto
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterRecordViewModel,
)

from .formatting import preview_text
from .workspace_mode import WorkspaceMode


def build_entry_state(entry: RegisterEntryResponseDto) -> dict[str, object]:
    def value(raw):
        return getattr(raw, "value", raw)

    return {
        "entryId": entry.id,
        "projectId": entry.project_id,
        "projectName": entry.project_name,
        "entryCode": getattr(entry, "code", "") or "",
        "type": value(entry.entry_type),
        "typeLabel": value(entry.entry_type).replace("_", " ").title(),
        "title": entry.title,
        "description": entry.description or "",
        "severity": value(entry.severity),
        "severityLabel": value(entry.severity).replace("_", " ").title(),
        "status": value(entry.status),
        "statusLabel": value(entry.status).replace("_", " ").title(),
        "ownerName": entry.owner_name or "",
        "dueDate": entry.due_date.isoformat() if entry.due_date else "",
        "dueDateLabel": entry.due_date.isoformat() if entry.due_date else "No due date",
        "impactSummary": entry.impact_summary or "",
        "responsePlan": entry.response_plan or "",
        "isOverdue": entry.is_overdue,
        "version": entry.version,
    }

def to_record_view_model(entry: RegisterEntryResponseDto, *, workspace_mode: WorkspaceMode) -> RegisterRecordViewModel:
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
        id=str(state["entryId"]),
        title=str(state["title"]),
        status_label=str(state["severityLabel"]),
        subtitle=" | ".join(str(part) for part in subtitle_parts if part),
        supporting_text=" | ".join(part for part in supporting_parts if part),
        meta_text=preview_text(
            str(state["responsePlan"]),
            str(state["impactSummary"]),
            str(state["description"]),
        ),
        state=state,
    )
