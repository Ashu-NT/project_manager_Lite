from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectCatalogReadItem,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectDetailFieldViewModel,
    ProjectDetailViewModel,
)

from .project_mapper import build_project_state


def build_detail_view_model(
    response: ProjectResponse | ProjectCatalogReadItem | None,
    *,
    department_labels: Mapping[str, str] | None = None,
) -> ProjectDetailViewModel:
    if response is None:
        return ProjectDetailViewModel(
            title="No project selected",
            empty_state="Select a project from the catalog to review details or edit its setup.",
        )
    state = build_project_state(response, department_labels=department_labels)
    project = (
        response.project if isinstance(response, ProjectCatalogReadItem) else response
    )
    client_label = str(state["clientLabel"] or "No client assigned")
    site_label = str(state["siteLabel"] or "No site assigned")
    fields = [
        ProjectDetailFieldViewModel(
            label="Client",
            value=client_label,
            supporting_text=str(state["clientContact"] or "No client contact recorded"),
        ),
        ProjectDetailFieldViewModel(label="Start", value=str(state["startDateLabel"])),
        ProjectDetailFieldViewModel(label="Finish", value=str(state["endDateLabel"])),
    ]
    if state["approvedBudgetVisible"]:
        fields.append(
            ProjectDetailFieldViewModel(
                label="Approved Budget",
                value=str(state["approvedBudgetLabel"]),
                supporting_text=str(state["approvedBudgetCurrency"]),
            )
        )
    fields.extend(
        (
            ProjectDetailFieldViewModel(label="Site", value=site_label),
            ProjectDetailFieldViewModel(label="Version", value=str(state["version"])),
        )
    )
    return ProjectDetailViewModel(
        id=project.id,
        title=project.name,
        status_label=str(state["statusLabel"]),
        subtitle=client_label,
        description=project.description or "No project description has been added yet.",
        fields=tuple(fields),
        state=state,
    )
