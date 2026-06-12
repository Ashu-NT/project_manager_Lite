from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerRecurringRowViewModel,
)


def recurring_row(row) -> MaintenancePlannerRecurringRowViewModel:
    return MaintenancePlannerRecurringRowViewModel(
        anchor_id=row.anchor_id,
        anchor_label=row.anchor_label,
        failure_name=row.failure_name,
        leading_root_cause_name=row.leading_root_cause_name,
        occurrence_count=row.occurrence_count,
        open_work_orders=row.open_work_orders,
        sensor_exception_count=row.sensor_exception_count,
    )
