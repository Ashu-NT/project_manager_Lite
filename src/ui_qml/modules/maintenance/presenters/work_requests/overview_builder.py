from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestMetricViewModel,
    MaintenanceWorkRequestOverviewViewModel,
)


def build_overview(*, all_rows, filtered_rows) -> MaintenanceWorkRequestOverviewViewModel:
    new_count = sum(1 for row in all_rows if row.status == "NEW")
    triaged_count = sum(1 for row in all_rows if row.status == "TRIAGED")
    approved_count = sum(1 for row in all_rows if row.status == "APPROVED")
    return MaintenanceWorkRequestOverviewViewModel(
        title="Work Requests",
        subtitle=(
            "Request intake, triage progression, and conversion-ready backlog now render "
            "through the maintenance desktop API."
        ),
        metrics=(
            MaintenanceWorkRequestMetricViewModel(
                label="Requests",
                value=str(len(all_rows)),
                supporting_text=f"Showing {len(filtered_rows)} requests with the current filters.",
            ),
            MaintenanceWorkRequestMetricViewModel(
                label="New",
                value=str(new_count),
                supporting_text="Fresh intake still waiting for first triage.",
            ),
            MaintenanceWorkRequestMetricViewModel(
                label="Triaged",
                value=str(triaged_count),
                supporting_text="Requests already assessed and ready for the next decision.",
            ),
            MaintenanceWorkRequestMetricViewModel(
                label="Approved",
                value=str(approved_count),
                supporting_text="Requests already approved for conversion or execution planning.",
            ),
        ),
    )
