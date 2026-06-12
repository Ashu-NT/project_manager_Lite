from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogMetricViewModel,
    ProjectCatalogOverviewViewModel,
)

def build_overview(
    *,
    all_projects: Any,
    filtered_projects: Any,
) -> ProjectCatalogOverviewViewModel:
    def count_by_status(status: str) -> int:
        return sum(1 for project in all_projects if project.status == status)

    return ProjectCatalogOverviewViewModel(
        title="Projects",
        subtitle="Project lifecycle, ownership, status, and list workflows.",
        metrics=(
            ProjectCatalogMetricViewModel(
                label="Total projects",
                value=str(len(all_projects)),
                supporting_text=f"Showing {len(filtered_projects)} with the current filters.",
            ),
            ProjectCatalogMetricViewModel(
                label="Active",
                value=str(count_by_status("ACTIVE")),
                supporting_text="Projects currently executing.",
            ),
            ProjectCatalogMetricViewModel(
                label="Planned",
                value=str(count_by_status("PLANNED")),
                supporting_text="Ready to start.",
            ),
            ProjectCatalogMetricViewModel(
                label="On hold",
                value=str(count_by_status("ON_HOLD")),
                supporting_text="Paused projects needing decisions.",
            ),
            ProjectCatalogMetricViewModel(
                label="Completed",
                value=str(count_by_status("COMPLETED")),
                supporting_text="Closed delivery work.",
            ),
        ),
    )

def build_empty_overview() -> ProjectCatalogOverviewViewModel:
    return ProjectCatalogOverviewViewModel(
        title="Projects",
        subtitle="Project lifecycle, ownership, status, and list workflows.",
        metrics=(),
    )
