from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.domain.risk.register import RegisterEntrySeverity
from src.ui_qml.modules.project_management.view_models.register import RegisterCollectionViewModel

from .entry_mapper import to_record_view_model
from .utils import WorkspaceMode, is_active

def urgent_entries(filtered_entries: Any) -> list[Any]:
    def sort_key(entry: Any) -> tuple[int, int, date, str]:
        severity_order = {
            RegisterEntrySeverity.CRITICAL.value: 0,
            RegisterEntrySeverity.HIGH.value: 1,
            RegisterEntrySeverity.MEDIUM.value: 2,
            RegisterEntrySeverity.LOW.value: 3,
        }
        due_date = entry.due_date or date.max
        return (
            severity_order.get(entry.severity, 99),
            0 if entry.is_overdue else 1,
            due_date,
            (entry.title or "").casefold(),
        )

    return sorted(
        [entry for entry in filtered_entries if is_active(entry.status)],
        key=sort_key,
    )

def build_urgent_collection(
    filtered_entries: Any,
    *,
    workspace_mode: WorkspaceMode,
) -> RegisterCollectionViewModel:
    urgent = tuple(
        to_record_view_model(entry, workspace_mode=workspace_mode)
        for entry in urgent_entries(filtered_entries)[:5]
    )
    return RegisterCollectionViewModel(
        title="Urgent Review Queue",
        subtitle="Severity-first shortlist to help triage what needs attention next.",
        empty_state=(
            "No urgent entries match the current filters."
            if filtered_entries
            else "No urgent entries are available for the current scope."
        ),
        items=urgent,
    )
