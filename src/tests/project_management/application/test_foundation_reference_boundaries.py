from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.core.modules.project_management.api.desktop.resources.builders.employee_option_builder import (
    build_employee_lookup,
)
from src.core.modules.project_management.api.desktop.resources.serializers.resource_serializer import (
    serialize_resource,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.common.exceptions import ValidationError


def test_employee_reference_requires_pm_employee_resource_registration(services):
    department = services["department_service"].create_department(
        department_code="DEP-BOUNDARY", name="Boundary Department"
    )
    employee = services["employee_service"].create_employee(
        employee_code="EMP-BOUNDARY", full_name="Boundary Employee", department_id=department.id
    )
    with pytest.raises(ValidationError, match="Only employee resources"):
        services["resource_service"].create_resource(
            "External", worker_type=WorkerType.EXTERNAL, employee_id=employee.id
        )


def test_resource_desktop_dto_uses_current_platform_employee_profile(services):
    department = services["department_service"].create_department(
        department_code="DEP-DISPLAY", name="Display Department"
    )
    employee_service = services["employee_service"]
    employee = employee_service.create_employee(
        employee_code="EMP-DISPLAY", full_name="Original Name",
        department_id=department.id, email="before@example.com",
    )
    resource = services["resource_service"].create_resource(
        "", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id
    )
    employee_service.update_employee(
        employee.id, full_name="Current Name", email="after@example.com",
        expected_version=employee.version,
    )
    dto = serialize_resource(
        services["resource_service"].get_resource(resource.id),
        employee_lookup=build_employee_lookup(employee_service),
    )
    assert dto.name == "Current Name"
    assert dto.contact == "after@example.com"
    assert dto.employee_id == employee.id


def test_project_client_party_is_platform_owned_and_scope_checked(services):
    party_service = services["party_service"]
    project_service = services["project_service"]
    client = party_service.create_party(party_code="CUST-BOUNDARY", party_name="Client")

    project = project_service.create_project(
        name="Party reference project", client_party_id=client.id
    )
    assert project.client_party_id == client.id

    party_service.deactivate_party(client.id)
    project_service.update_project(project.id, name="Renamed project")
    with pytest.raises(ValidationError, match="inactive"):
        project_service.create_project(
            name="New party link", client_party_id=client.id
        )
    with pytest.raises(ValidationError, match="not found"):
        project_service.create_project(
            name="Foreign party link", client_party_id="not-a-party"
        )


def test_project_department_reference_is_optional_and_platform_owned(services):
    project_service = services["project_service"]
    department_service = services["department_service"]
    project = project_service.create_project(name="No department project")
    assert project.department_id is None

    department = department_service.create_department(
        department_code="DEP-PROJECT", name="Project Department"
    )
    linked = project_service.create_project(
        name="Linked department project", department_id=department.id
    )
    assert linked.department_id == department.id
    department_service.deactivate_department(department.id)
    project_service.update_project(linked.id, name="Historical department project")
    with pytest.raises(ValidationError, match="inactive"):
        project_service.create_project(
            name="New department project", department_id=department.id
        )
    with pytest.raises(ValidationError, match="not found"):
        project_service.create_project(
            name="Unknown department project", department_id="not-a-department"
        )


def test_platform_master_data_and_composition_do_not_import_pm():
    root = Path(__file__).resolve().parents[4]
    paths = [root / "src/infra/composition/modules/platform_registry.py"]
    paths.extend((root / "src/core/platform/application/master_data").rglob("*.py"))
    paths.extend((root / "src/core/platform/contract").rglob("*.py"))
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = (
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert not any(module.startswith("src.core.modules.project_management") for module in imports), path
