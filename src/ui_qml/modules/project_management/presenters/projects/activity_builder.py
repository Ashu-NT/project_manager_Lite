from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview


def build_project_activity_state(*, project_id: str) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_activity=ProjectSectionCollectionViewModel(
            title="Activity",
            subtitle="Recent project activity.",
            empty_state="Open the Collaboration workspace to view the full project activity feed.",
            items=(),
        ),
    )
