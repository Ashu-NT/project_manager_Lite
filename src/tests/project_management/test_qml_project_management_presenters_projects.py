from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.domain.enums import ProjectStatus


def test_project_management_workspace_catalog_exposes_typed_projects_controller() -> None:
    projects_api = build_project_management_projects_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(
                    id="proj-1",
                    name="Plant Upgrade",
                    description="Replace switchgear and commission the new line.",
                    status=ProjectStatus.ACTIVE,
                    start_date=date(2026, 5, 1),
                    end_date=date(2026, 8, 15),
                    client_name="Contoso Manufacturing",
                    client_contact="alex@contoso.example",
                    planned_budget=250000.0,
                    currency="EUR",
                    version=4,
                ),
                SimpleNamespace(
                    id="proj-2",
                    name="Warehouse Retrofit",
                    description="Upgrade lighting and controls.",
                    status=ProjectStatus.ON_HOLD,
                    start_date=None,
                    end_date=None,
                    client_name="Northwind Logistics",
                    client_contact="jamie@northwind.example",
                    planned_budget=None,
                    currency=None,
                    version=2,
                ),
            ]
        )
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_projects=projects_api)
    )

    controller = catalog.projectsWorkspace

    assert controller.workspace["routeId"] == "project_management.projects"
    assert controller.overview["title"] == "Projects"
    assert controller.overview["metrics"][0]["value"] == "2"
    assert controller.projects["items"][0]["title"] == "Plant Upgrade"
    assert controller.selectedProject["title"] == "Plant Upgrade"

    controller.setStatusFilter("ON_HOLD")

    assert controller.selectedStatusFilter == "ON_HOLD"
    assert controller.projects["items"][0]["title"] == "Warehouse Retrofit"

    controller.setSearchText("plant")

    assert controller.projects["items"] == []
    assert controller.emptyState == "No projects match the current filters."
