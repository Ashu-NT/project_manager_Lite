from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerRequestRowViewModel,
)


def request_row(row) -> MaintenancePlannerRequestRowViewModel:
    return MaintenancePlannerRequestRowViewModel(
        id=row.id,
        request_label=row.request_label,
        anchor_label=row.anchor_label,
        status_label=row.status_label,
        priority_label=row.priority_label,
    )
