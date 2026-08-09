from __future__ import annotations

from typing import Any
from src.ui_qml.modules.project_management.view_models.register import RegisterCollectionViewModel

from .entry_mapper import to_record_view_model
from .utils import WorkspaceMode

def build_urgent_collection(
    filtered_entries: Any,
    *,
    filtered_total: int,
    workspace_mode: WorkspaceMode,
) -> RegisterCollectionViewModel:
    urgent = tuple(
        to_record_view_model(entry, workspace_mode=workspace_mode)
        for entry in filtered_entries
    )
    return RegisterCollectionViewModel(
        title="Urgent Review Queue",
        subtitle="Severity-first shortlist to help triage what needs attention next.",
        empty_state=(
            "No urgent entries match the current filters."
            if filtered_total
            else "No urgent entries are available for the current scope."
        ),
        items=urgent,
    )
