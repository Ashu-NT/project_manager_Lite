from __future__ import annotations

from src.core.modules.project_management.api.desktop.register import (
    ProjectManagementRegisterDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview


def build_project_risks_state(
    register_desktop_api: ProjectManagementRegisterDesktopApi,
    *,
    project_id: str,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    risks = (
        register_desktop_api.list_entries(
            project_id=normalized_project_id,
            entry_type="RISK",
        )
        if normalized_project_id
        else ()
    )
    items = tuple(
        ProjectRecordViewModel(
            id=risk.id,
            title=risk.title,
            status_label=risk.severity_label,
            subtitle=risk.status_label,
            supporting_text=risk.impact_summary or "No impact summary recorded.",
            meta_text=risk.due_date_label,
        )
        for risk in risks
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_risks=ProjectSectionCollectionViewModel(
            title="Risks",
            subtitle=f"{len(items)} risk(s) recorded." if items else "Risks and mitigation records.",
            empty_state="No risks have been logged for this project yet.",
            items=items,
        ),
    )
