from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_projects_desktop_api,
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.api.desktop.projects.commands.project_commands import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.projects.project import Project


def test_project_management_projects_desktop_api_lists_statuses() -> None:
    api = build_project_management_projects_desktop_api()

    statuses = api.list_statuses()

    assert [status.value for status in statuses] == [
        "PLANNED",
        "ACTIVE",
        "ON_HOLD",
        "COMPLETED",
    ]
    assert statuses[2].label == "On Hold"


def test_project_management_projects_desktop_api_mutates_project_records() -> None:
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(project_service=service)

    created = api.create_project(
        ProjectCreateCommand(
            name="Plant Upgrade",
            description="Replace switchgear and commission the new line.",
            status="ACTIVE",
            client_name="Contoso Manufacturing",
            client_contact="alex@contoso.example",
            financial_currency_code="eur",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 15),
        )
    )

    listed = api.list_projects()

    assert created.status == "ACTIVE"
    assert listed[0].approved_budget_label == "Not set"
    assert listed[0].status_label == "Active"

    updated = api.update_project(
        ProjectUpdateCommand(
            project_id=created.id,
            expected_version=service.get_project(created.id).version,
            name="Plant Upgrade Phase 1",
            description="Updated execution scope.",
            status="ON_HOLD",
            client_name="Contoso Manufacturing",
            client_contact="jamie@contoso.example",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 8, 20),
        )
    )

    assert updated.name == "Plant Upgrade Phase 1"
    assert updated.status == "ON_HOLD"
    assert updated.approved_budget_label == "Not set"

    completed = api.set_project_status(created.id, "COMPLETED")

    assert completed.status == "COMPLETED"
    assert completed.status_label == "Completed"

    api.delete_project(created.id)

    assert api.list_projects() == ()


def test_project_management_projects_desktop_api_get_project_by_id() -> None:
    """R2.3: PMProjectContextController resolves a single project by id
    through this method -- added because it didn't previously exist on the
    desktop API even though the underlying service already supported it."""
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(project_service=service)
    created = api.create_project(
        ProjectCreateCommand(
            name="Harbor Expansion",
            description="Dredge and extend berth 4.",
            status="ACTIVE",
            client_name="",
            client_contact="",
            financial_currency_code="eur",
            start_date=None,
            end_date=None,
        )
    )

    found = api.get_project(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.name == "Harbor Expansion"
    assert found.status_label == "Active"


def test_project_management_projects_desktop_api_get_project_missing_returns_none() -> None:
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(project_service=service)

    assert api.get_project("does-not-exist") is None


def test_project_management_projects_desktop_api_get_project_without_service_returns_none() -> None:
    api = build_project_management_projects_desktop_api()

    assert api.get_project("anything") is None


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        financial_currency_code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str = "",
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def update_project(
        self,
        project_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        organization_id: str | None = None,
        site_id: str | None = None,
        client_party_id: str | None = None,
        manager_user_id: str | None = None,
        code: str | None = None,
    ) -> Project:
        project = self._projects[project_id]
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name
        if client_contact is not None:
            project.client_contact = client_contact
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)
