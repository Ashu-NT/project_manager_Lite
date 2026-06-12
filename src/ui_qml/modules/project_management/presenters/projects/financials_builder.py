from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview


def build_project_financials_state(*, project_id: str) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_financials=ProjectSectionCollectionViewModel(
            title="Financials",
            subtitle="Budget, cost, and financial tracking.",
            empty_state="Open the Financials workspace to review cost and budget details.",
            items=(),
        ),
    )
