from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.reliability import (
    MaintenanceReliabilityInsightRowViewModel,
)


def root_cause_row(row) -> MaintenanceReliabilityInsightRowViewModel:
    return MaintenanceReliabilityInsightRowViewModel(
        failure_name=row.failure_name,
        root_cause_name=row.root_cause_name,
        work_order_count=row.work_order_count,
        total_downtime_minutes=row.total_downtime_minutes,
        open_work_orders=row.open_work_orders,
    )
