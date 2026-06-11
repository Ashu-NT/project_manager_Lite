from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerWorkOrderRowViewModel,
)


def work_order_row(row) -> MaintenancePlannerWorkOrderRowViewModel:
    return MaintenancePlannerWorkOrderRowViewModel(
        id=row.id,
        work_order_label=row.work_order_label,
        work_order_type_label=row.work_order_type_label,
        status_label=row.status_label,
        priority_label=row.priority_label,
        plan_window_label=row.plan_window_label,
    )
