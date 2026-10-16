from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
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
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectCatalogReadPage,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceCatalogReadPage,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project


def test_project_handlers_return_immutable_application_responses(services) -> None:
    created = services["project_create"].create_project(
        ProjectCreateCommand(name="Typed project boundary", description="Preserve this", status="ACTIVE")
    )
    assert isinstance(created, ProjectResponse)
    assert not isinstance(created, Project)
    updated = services["project_update"].update_project(
        ProjectUpdateCommand(project_id=created.id, name="Typed project renamed", expected_version=created.version)
    )
    assert isinstance(updated, ProjectResponse)
    assert updated.description == "Preserve this"
    assert updated.status == ProjectStatus.ACTIVE
    queried = services["project_query"].get_project(created.id)
    assert isinstance(queried, ProjectResponse)
    assert queried.name == updated.name
    with pytest.raises(FrozenInstanceError):
        setattr(queried, "name", "Not a domain mutation")


@pytest.mark.parametrize("visible", [True, False])
def test_project_response_preserves_zero_and_redaction(visible: bool) -> None:
    result = map_project_response(
        Project.create("Zero budget project"),
        approved_budget=Decimal("0.00"),
        approved_budget_currency="XAF",
        approved_budget_visible=visible,
    )
    assert result.approved_budget == (Decimal("0.00") if visible else None)
    assert result.approved_budget_currency == ("XAF" if visible else "")
    assert result.approved_budget_visible is visible


def test_catalog_queries_reuse_reader_dtos_without_response_copies(services) -> None:
    project_page = services["project_query"].query_catalog_page()
    resource_page = services["resource_query"].query_catalog_page()
    assert type(project_page) is ProjectCatalogReadPage
    assert type(resource_page) is ResourceCatalogReadPage


def test_resource_write_maps_domain_but_read_reuses_its_reader_dto(services) -> None:
    resource = services["resource_master_commands"].create_resource(
        ResourceCreateCommand(name="Canonical resource DTO boundary")
    )
    assert type(resource) is ResourceResponse
    page = services["resource_query"].query_catalog_page(search_text=resource.name)
    assert type(page) is ResourceCatalogReadPage
    assert any(item.resource_id == resource.id for item in page.items)


def test_project_desktop_consumes_application_response_and_forwards_command_unchanged(services) -> None:
    api = ProjectManagementProjectsDesktopApi(project_create=services["project_create"])
    result = api.create_project(ProjectCreateCommand(name="Desktop typed project", status="ACTIVE"))
    assert result.name == "Desktop typed project"
    assert result.status == "ACTIVE"
    assert result.status_label == "Active"
