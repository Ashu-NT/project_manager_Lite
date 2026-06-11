from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilitySuggestionRowViewModel,
)


def suggestion_row(row) -> MaintenanceReliabilitySuggestionRowViewModel:
    return MaintenanceReliabilitySuggestionRowViewModel(
        match_scope_label=row.match_scope_label,
        root_cause_name=row.root_cause_name,
        occurrence_count=row.occurrence_count,
        total_downtime_minutes=row.total_downtime_minutes,
        latest_occurrence_at_label=row.latest_occurrence_at_label,
    )
