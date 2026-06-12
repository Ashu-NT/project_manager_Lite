from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.preventive import (
    MaintenancePreventiveMetricViewModel,
    MaintenancePreventiveOverviewViewModel,
)


def build_overview(
    *,
    queue_rows,
    plan_rows,
    task_template_rows,
) -> MaintenancePreventiveOverviewViewModel:
    due_count = sum(1 for row in queue_rows if row.due_state == "DUE")
    due_soon_count = sum(1 for row in queue_rows if row.is_due_soon)
    blocked_count = sum(1 for row in queue_rows if row.due_state == "BLOCKED")
    return MaintenancePreventiveOverviewViewModel(
        title="Preventive",
        subtitle=(
            "Preventive queue, plan-library governance, and task-template "
            "migration now run through the maintenance preventive desktop API."
        ),
        metrics=(
            MaintenancePreventiveMetricViewModel(
                label="Queue",
                value=str(len(queue_rows)),
                supporting_text=(
                    f"{due_count} due, {due_soon_count} due soon, "
                    f"{blocked_count} blocked."
                ),
            ),
            MaintenancePreventiveMetricViewModel(
                label="Plans",
                value=str(len(plan_rows)),
                supporting_text=(
                    "Preventive plans currently available in the typed library."
                ),
            ),
            MaintenancePreventiveMetricViewModel(
                label="Templates",
                value=str(len(task_template_rows)),
                supporting_text=(
                    "Reusable task templates and step libraries available for "
                    "plan tasks."
                ),
            ),
        ),
    )
