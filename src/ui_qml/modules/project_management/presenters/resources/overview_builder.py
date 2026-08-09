from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCatalogMetricViewModel,
    ResourceCatalogOverviewViewModel,
)

def build_overview(
    *,
    total: int,
    filtered_total: int,
    active: int,
    employees: int,
    external: int,
    average_capacity: float,
) -> ResourceCatalogOverviewViewModel:
    return ResourceCatalogOverviewViewModel(
        title="Resources",
        subtitle="Resource capacity, staffing type, and pool availability workflows.",
        metrics=(
            ResourceCatalogMetricViewModel(
                label="Total resources",
                value=str(total),
                supporting_text=f"Showing {filtered_total} with the current filters.",
            ),
            ResourceCatalogMetricViewModel(
                label="Active",
                value=str(active),
                supporting_text="Resources currently available for assignment.",
            ),
            ResourceCatalogMetricViewModel(
                label="Employees",
                value=str(employees),
                supporting_text="Resources linked to the shared employee directory.",
            ),
            ResourceCatalogMetricViewModel(
                label="External",
                value=str(external),
                supporting_text="Vendor or contract resources managed locally in PM.",
            ),
            ResourceCatalogMetricViewModel(
                label="Avg capacity",
                value=f"{average_capacity:.1f}%",
                supporting_text="Average capacity across the current PM resource pool.",
            ),
        ),
    )
