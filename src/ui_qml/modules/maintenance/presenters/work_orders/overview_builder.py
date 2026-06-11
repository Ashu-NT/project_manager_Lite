from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrderMetricViewModel,
    MaintenanceWorkOrderOverviewViewModel,
)


def build_overview(*, all_rows, filtered_rows) -> MaintenanceWorkOrderOverviewViewModel:
    draft_count = sum(1 for row in all_rows if row.status == "DRAFT")
    planned_count = sum(1 for row in all_rows if row.status == "PLANNED")
    active_count = sum(1 for row in all_rows if row.status == "IN_PROGRESS")
    return MaintenanceWorkOrderOverviewViewModel(
        title="Work Orders",
        subtitle=(
            "Execution planning, assignment readiness, and lifecycle control now render "
            "through the maintenance desktop API."
        ),
        metrics=(
            MaintenanceWorkOrderMetricViewModel(
                label="Orders",
                value=str(len(all_rows)),
                supporting_text=f"Showing {len(filtered_rows)} work orders with the current filters.",
            ),
            MaintenanceWorkOrderMetricViewModel(
                label="Draft",
                value=str(draft_count),
                supporting_text="New execution records still waiting for planning detail.",
            ),
            MaintenanceWorkOrderMetricViewModel(
                label="Planned",
                value=str(planned_count),
                supporting_text="Planned work that is ready for scheduling and release.",
            ),
            MaintenanceWorkOrderMetricViewModel(
                label="Active",
                value=str(active_count),
                supporting_text="Orders already released into execution or currently in progress.",
            ),
        ),
    )
