from __future__ import annotations

from typing import Any

from src.core.modules.project_management.domain.enums import WorkerType
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCatalogMetricViewModel,
    ResourceCatalogOverviewViewModel,
)

def build_overview(*, all_resources: Any, filtered_resources: Any) -> ResourceCatalogOverviewViewModel:
    total_capacity = sum(float(resource.capacity_percent or 0.0) for resource in all_resources)
    average_capacity = total_capacity / len(all_resources) if all_resources else 0.0
    employee_count = sum(
        1 for resource in all_resources if resource.worker_type == WorkerType.EMPLOYEE.value
    )
    external_count = sum(
        1 for resource in all_resources if resource.worker_type == WorkerType.EXTERNAL.value
    )
    active_count = sum(1 for resource in all_resources if resource.is_active)
    return ResourceCatalogOverviewViewModel(
        title="Resources",
        subtitle="Resource capacity, staffing type, and pool availability workflows.",
        metrics=(
            ResourceCatalogMetricViewModel(
                label="Total resources",
                value=str(len(all_resources)),
                supporting_text=f"Showing {len(filtered_resources)} with the current filters.",
            ),
            ResourceCatalogMetricViewModel(
                label="Active",
                value=str(active_count),
                supporting_text="Resources currently available for assignment.",
            ),
            ResourceCatalogMetricViewModel(
                label="Employees",
                value=str(employee_count),
                supporting_text="Resources linked to the shared employee directory.",
            ),
            ResourceCatalogMetricViewModel(
                label="External",
                value=str(external_count),
                supporting_text="Vendor or contract resources managed locally in PM.",
            ),
            ResourceCatalogMetricViewModel(
                label="Avg capacity",
                value=f"{average_capacity:.1f}%",
                supporting_text="Average capacity across the current PM resource pool.",
            ),
        ),
    )
