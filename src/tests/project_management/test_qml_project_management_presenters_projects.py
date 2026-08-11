from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.domain.enums import ProjectStatus


def test_project_management_workspace_catalog_exposes_typed_projects_controller() -> None:
    projects = [
        SimpleNamespace(
            id="proj-1",
            name="Plant Upgrade",
            description="Replace switchgear and commission the new line.",
            status=ProjectStatus.ACTIVE,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 15),
            client_name="Contoso Manufacturing",
            client_contact="alex@contoso.example",
            site_id=None,
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
            site_id=None,
            version=2,
        ),
    ]

    def query_catalog_page(*, search_text, status, page, page_size):
        filtered = [
            project
            for project in projects
            if (status is None or project.status == status)
            and (
                not search_text
                or search_text.casefold()
                in " ".join(
                    (
                        project.name,
                        project.client_name or "",
                        project.client_contact or "",
                        project.description,
                    )
                ).casefold()
            )
        ]
        offset = (page - 1) * page_size
        return SimpleNamespace(
            items=tuple(
                SimpleNamespace(
                    project=project,
                    site_label="",
                    financial_currency_code=("EUR" if project.id == "proj-1" else ""),
                    approved_budget=(250000.0 if project.id == "proj-1" else None),
                )
                for project in filtered[offset : offset + page_size]
            ),
            filtered_total=len(filtered),
            page=page,
            page_size=page_size,
            summary=SimpleNamespace(
                total=len(projects),
                active=sum(project.status == ProjectStatus.ACTIVE for project in projects),
                planned=sum(project.status == ProjectStatus.PLANNED for project in projects),
                on_hold=sum(project.status == ProjectStatus.ON_HOLD for project in projects),
                completed=sum(project.status == ProjectStatus.COMPLETED for project in projects),
            ),
        )

    projects_api = build_project_management_projects_desktop_api(
        project_service=SimpleNamespace(
            query_catalog_page=query_catalog_page,
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
