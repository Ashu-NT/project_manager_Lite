from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from typing import cast

import pytest

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_resources import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceMasterCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.skill_commands import (
    ResourceCapabilityCommandHandler,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.certifications import (
    ResourceAddCertificationCommand,
)
from src.core.modules.project_management.application.resources.dto.responses.capabilities import (
    ResourceCertificationResponse,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.application.resources.dto.responses.project_resources import (
    ProjectResourceResponse,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryHandler,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectResourceUsageFact,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceCatalogReadItem,
)


def test_resource_command_reaches_composed_handler_and_returns_response(
    services: dict[str, object], monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = cast(ResourceMasterCommandHandler, services["resource_master_commands"])
    original = handler.create_resource
    command = ResourceCreateCommand(name="  Boundary resource  ", hourly_rate=Decimal("12.5"))
    observed: list[ResourceResponse] = []

    def capture(received: ResourceCreateCommand) -> ResourceResponse:
        assert received is command
        response = original(received)
        assert isinstance(response, ResourceResponse)
        observed.append(response)
        return response

    monkeypatch.setattr(handler, "create_resource", capture)
    api = ProjectManagementResourcesDesktopApi(resource_master_commands=handler)
    desktop = api.create_resource(command)
    assert desktop is observed[0]
    assert desktop.name == "Boundary resource"
    assert observed[0].hourly_rate == Decimal("12.5")
    with pytest.raises(FrozenInstanceError):
        setattr(observed[0], "name", "changed")


def test_resource_update_command_identity_and_noop_response(
    services: dict[str, object], monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = cast(ResourceMasterCommandHandler, services["resource_master_commands"])
    resource = handler.create_resource(ResourceCreateCommand(name="Noop boundary"))
    command = ResourceUpdateCommand(
        resource_id=resource.id, expected_version=resource.version,
        name=resource.name, code=resource.code, kind=resource.kind.value,
        role=resource.role, hourly_rate=resource.hourly_rate, cost_type=resource.cost_type.value,
        currency_code=resource.currency_code, capacity_percent=resource.capacity_percent,
        address=resource.address, contact=resource.contact, worker_type=resource.worker_type.value,
        employee_id=resource.employee_id, department_id=resource.department_id, site_id=resource.site_id,
    )
    original = handler.update_resource

    def capture(received: ResourceUpdateCommand) -> ResourceResponse:
        assert received is command
        response = original(received)
        assert response == resource
        return response

    monkeypatch.setattr(handler, "update_resource", capture)
    desktop = ProjectManagementResourcesDesktopApi(resource_master_commands=handler).update_resource(command)
    assert desktop.version == resource.version


def test_certification_dates_are_normalized_inside_composed_handler(
    services: dict[str, object], monkeypatch: pytest.MonkeyPatch,
) -> None:
    master = cast(ResourceMasterCommandHandler, services["resource_master_commands"])
    handler = cast(ResourceCapabilityCommandHandler, services["resource_capability_commands"])
    resource = master.create_resource(ResourceCreateCommand(name="Certification boundary"))
    command = ResourceAddCertificationCommand(
        resource_id=resource.id, certification_code="safety", certification_name="Safety",
        issued_date=" 2026-01-02 ", expiry_date="2027-01-02",
    )
    original = handler.add_resource_certification

    def capture(received: ResourceAddCertificationCommand) -> ResourceCertificationResponse:
        assert received is command
        response = original(received)
        assert isinstance(response, ResourceCertificationResponse)
        assert response.issued_date == date(2026, 1, 2)
        return response

    monkeypatch.setattr(handler, "add_resource_certification", capture)
    desktop = ProjectManagementResourcesDesktopApi(resource_capability_commands=handler).add_resource_certification(command)
    assert desktop.issued_date == date(2026, 1, 2)


def test_project_resource_command_identity_and_application_response(
    services: dict[str, object], monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = cast(ProjectCreateHandler, services["project_create"]).create_project(ProjectCreateCommand(name="Resource boundary"))
    resource = cast(ResourceMasterCommandHandler, services["resource_master_commands"]).create_resource(ResourceCreateCommand(name="Assigned boundary"))
    handler = cast(ProjectResourceCommandHandler, services["project_resource_commands"])
    query = cast(ProjectResourceQueryHandler, services["project_resource_query"])
    command = ProjectResourceAssignCommand(
        project_id=f" {project.id} ", resource_id=f" {resource.id} ", planned_hours=Decimal(12),
    )
    original = handler.add_to_project

    def capture(received: ProjectResourceAssignCommand) -> ProjectResourceResponse:
        assert received is command
        response = original(received)
        assert isinstance(response, ProjectResourceResponse)
        assert response.project_id == project.id
        return response

    monkeypatch.setattr(handler, "add_to_project", capture)
    api = ProjectManagementProjectsDesktopApi(
        project_resource_commands=handler,
        resource_query=cast(ResourceQueryHandler, services["resource_query"]),
    )
    desktop = api.add_project_resource(command)
    update = ProjectResourceUpdateCommand(
        project_resource_id=desktop.id, planned_hours=Decimal(15), expected_version=desktop.version,
    )
    original_update = handler.update

    def capture_update(received: ProjectResourceUpdateCommand) -> None:
        assert received is update
        original_update(received)

    monkeypatch.setattr(handler, "update", capture_update)
    api.update_project_resource(update)
    response = query.get(desktop.id)
    assert isinstance(response, ProjectResourceResponse)
    assert response.planned_hours == Decimal(15)
    assert isinstance(query.get_usage(desktop.id), ProjectResourceUsageFact)


def test_composed_resource_reads_return_detached_response_dtos(services: dict[str, object]) -> None:
    handler = cast(ResourceMasterCommandHandler, services["resource_master_commands"])
    query = cast(ResourceQueryHandler, services["resource_query"])
    created = handler.create_resource(ResourceCreateCommand(name="Read boundary"))
    assert isinstance(query.get_resource(created.id), ResourceResponse)
    assert isinstance(query.list_resources()[0], ResourceResponse)
    page = query.query_catalog_page()
    assert isinstance(page.items[0], ResourceCatalogReadItem)
    assert not hasattr(page.items[0], "capacity_label")
    detached = replace(query.get_resource(created.id), name="Detached")
    assert detached.name == "Detached"
    assert query.get_resource(created.id).name == "Read boundary"
