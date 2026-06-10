from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.register import (
    RegisterDetailFieldViewModel,
    RegisterDetailViewModel,
)

from .entry_mapper import build_entry_state
from .utils import WorkspaceMode


def build_detail_view_model(entry, *, workspace_mode: WorkspaceMode) -> RegisterDetailViewModel:
    if entry is None:
        return RegisterDetailViewModel(
            title="No entry selected",
            empty_state=(
                "Select a risk entry to review mitigation details."
                if workspace_mode == "risk"
                else "Select a register entry to review governance details."
            ),
        )
    state = build_entry_state(entry)
    subtitle_values = [
        state["projectName"],
        state["typeLabel"],
        state["statusLabel"],
    ]
    return RegisterDetailViewModel(
        id=entry.id,
        title=entry.title,
        status_label=entry.severity_label,
        subtitle=" | ".join(value for value in subtitle_values if value),
        description=entry.description or "No description has been captured yet.",
        fields=(
            RegisterDetailFieldViewModel(
                label="Owner",
                value=entry.owner_name or "Unassigned",
            ),
            RegisterDetailFieldViewModel(
                label="Due date",
                value=entry.due_date_label,
                supporting_text=(
                    "Entry is overdue."
                    if entry.is_overdue
                    else "No escalation due date has been set."
                    if entry.due_date is None
                    else ""
                ),
            ),
            RegisterDetailFieldViewModel(
                label="Impact",
                value=entry.impact_summary or "No impact summary recorded.",
            ),
            RegisterDetailFieldViewModel(
                label="Response plan",
                value=entry.response_plan or "No response plan recorded.",
            ),
            RegisterDetailFieldViewModel(
                label="Version",
                value=str(entry.version),
            ),
        ),
        state=state,
    )
