from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardRootCauseRowViewModel,
)


def root_cause_row(row) -> MaintenanceDashboardRootCauseRowViewModel:
    return MaintenanceDashboardRootCauseRowViewModel(
        failure_name=row.failure_name,
        root_cause_name=row.root_cause_name,
        work_order_count=row.work_order_count,
        total_downtime_minutes=row.total_downtime_minutes,
        latest_occurrence_at_label=row.latest_occurrence_at_label,
        open_work_orders=row.open_work_orders,
    )
