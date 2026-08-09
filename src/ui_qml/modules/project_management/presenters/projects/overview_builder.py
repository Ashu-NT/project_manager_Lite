from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogMetricViewModel,
    ProjectCatalogOverviewViewModel,
)

def build_overview(
    *,
    total: int,
    filtered_total: int,
    active: int,
    planned: int,
    on_hold: int,
    completed: int,
) -> ProjectCatalogOverviewViewModel:
    return ProjectCatalogOverviewViewModel(
        title="Projects",
        subtitle="Project lifecycle, ownership, status, and list workflows.",
        metrics=(
            ProjectCatalogMetricViewModel(
                label="Total projects",
                value=str(total),
                supporting_text=f"Showing {filtered_total} with the current filters.",
            ),
            ProjectCatalogMetricViewModel(
                label="Active",
                value=str(active),
                supporting_text="Projects currently executing.",
            ),
            ProjectCatalogMetricViewModel(
                label="Planned",
                value=str(planned),
                supporting_text="Ready to start.",
            ),
            ProjectCatalogMetricViewModel(
                label="On hold",
                value=str(on_hold),
                supporting_text="Paused projects needing decisions.",
            ),
            ProjectCatalogMetricViewModel(
                label="Completed",
                value=str(completed),
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
