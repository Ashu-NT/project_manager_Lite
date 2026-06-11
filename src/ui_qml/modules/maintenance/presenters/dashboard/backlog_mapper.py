from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardBacklogRowViewModel,
)


def backlog_row(row) -> MaintenanceDashboardBacklogRowViewModel:
    return MaintenanceDashboardBacklogRowViewModel(
        group=row.group,
        label=row.label,
        value=row.value,
    )
