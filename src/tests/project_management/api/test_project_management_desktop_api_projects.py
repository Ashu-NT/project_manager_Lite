
from dataclasses import asdict
from datetime import date
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop import (
    build_project_management_projects_desktop_api,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.mappers.project import (
    map_project_response,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectCatalogProjectFact,
    ProjectCatalogReadItem,
)
from src.core.modules.project_management.domain.enums import (
    ProjectStatus,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.common.exceptions import BusinessRuleError


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


def test_project_query_checks_module_entitlement_before_repository() -> None:
    from src.core.modules.project_management.application.projects.queries.project_query import (
        ProjectQueryHandler,
    )

    catalog = SimpleNamespace(
        get_entitlement=lambda _code: SimpleNamespace(
            runtime_enabled=False,
            label="Project Management",
            lifecycle_status="inactive",
        )
    )
    query = ProjectQueryHandler(
        project_repo=SimpleNamespace(list=lambda: pytest.fail("repository called")),
        project_catalog_reader=None, tenant_context_service=None,
        user_session=None, module_catalog_service=catalog,
    )
    api = build_project_management_projects_desktop_api(
        project_query=query
    )

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled"):
        api.list_projects()


def test_project_management_projects_desktop_api_mutates_project_records() -> None:
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(
        project_create=service, project_update=service,
        project_status=service, project_deletion=service, project_query=service
    )

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
    assert listed[0].approved_budget_label == ""
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
    assert updated.approved_budget_label == ""

    completed = api.set_project_status(created.id, "COMPLETED")

    assert completed.status == "COMPLETED"
    assert completed.status_label == "Completed"

    api.delete_project(created.id)

    assert api.list_projects() == ()


def test_project_management_projects_desktop_api_get_project_by_id() -> None:
    """Resolves a single project by id through the desktop API."""
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(
        project_create=service, project_update=service,
        project_status=service, project_deletion=service, project_query=service
    )
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
    api = build_project_management_projects_desktop_api(
        project_create=service, project_update=service,
        project_status=service, project_deletion=service, project_query=service
    )

    assert api.get_project("does-not-exist") is None


def test_project_management_projects_desktop_api_get_project_without_service_returns_none() -> None:
    api = build_project_management_projects_desktop_api()

    assert api.get_project("anything") is None


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return [map_project_response(project) for project in self._projects.values()]

    def query_project_detail(self, project_id: str) -> ProjectCatalogReadItem | None:
        project = self._projects.get(project_id)
        if project is None:
            return None
        return ProjectCatalogReadItem(
            project=ProjectCatalogProjectFact(**asdict(project)),
            site_label="",
            financial_currency_code="",
            approved_budget=None,
            approved_budget_currency="",
            approved_budget_visible=True,
            client_label="",
        )

    def create_project(self, command: ProjectCreateCommand) -> ProjectResponse:
        project = Project(
            id=f"proj-{self._next_id}",
            name=command.name,
            description=command.description,
            start_date=command.start_date,
            end_date=command.end_date,
            status=ProjectStatus(command.status),
            client_name=command.client_name,
            client_contact=command.client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return map_project_response(project)

    def update_project(self, command: ProjectUpdateCommand) -> ProjectResponse:
        project = self._projects[command.project_id]
        if command.name is not None:
            project.name = command.name
        if command.description is not None:
            project.description = command.description
        if command.status is not None:
            project.status = ProjectStatus(command.status)
        if command.start_date is not None:
            project.start_date = command.start_date
        if command.end_date is not None:
            project.end_date = command.end_date
        if command.client_name is not None:
            project.client_name = command.client_name
        if command.client_contact is not None:
            project.client_contact = command.client_contact
        project.version += 1
        return map_project_response(project)

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]

    def get_project(self, project_id: str) -> Project | None:
        project = self._projects.get(project_id)
        return None if project is None else map_project_response(project)
