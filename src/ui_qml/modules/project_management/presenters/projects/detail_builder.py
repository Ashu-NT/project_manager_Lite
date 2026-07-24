from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectDetailFieldViewModel,
    ProjectDetailViewModel,
)

from .project_mapper import build_project_state

def build_detail_view_model(project: Any) -> ProjectDetailViewModel:
    if project is None:
        return ProjectDetailViewModel(
            title="No project selected",
            empty_state="Select a project from the catalog to review details or edit its setup.",
        )
    state = build_project_state(project)
    client_label = state["clientName"] or "No client assigned"
    site_label = state["siteLabel"] or "No site assigned"
    return ProjectDetailViewModel(
        id=project.id,
        title=project.name,
        status_label=project.status_label,
        subtitle=client_label,
        description=project.description or "No project description has been added yet.",
        fields=(
            ProjectDetailFieldViewModel(
                label="Client",
                value=client_label,
                supporting_text=state["clientContact"] or "No client contact recorded",
            ),
            ProjectDetailFieldViewModel(label="Start", value=state["startDateLabel"]),
            ProjectDetailFieldViewModel(label="Finish", value=state["endDateLabel"]),
            ProjectDetailFieldViewModel(
                label="Budget",
                value=state["plannedBudgetLabel"],
                supporting_text=state["currency"] or "Currency follows project defaults",
            ),
            ProjectDetailFieldViewModel(label="Site", value=site_label),
            ProjectDetailFieldViewModel(label="Version", value=str(state["version"])),
        ),
        state=state,
    )
