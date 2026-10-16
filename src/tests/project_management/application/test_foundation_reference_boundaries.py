from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.resources.dto.commands.catalog import (
    ResourceCreateCommand,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.party.dto.commands.party import (
    PartyCreateCommand,
)
from src.core.platform.common.exceptions import ValidationError
from src.ui_qml.modules.project_management.presenters.resources.detail_builder import (
    build_detail_view_model,
)


def test_employee_reference_requires_pm_employee_resource_registration(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="DEP-BOUNDARY", name="Boundary Department"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EMP-BOUNDARY", full_name="Boundary Employee", department_id=department.id))
    with pytest.raises(ValidationError, match="Only employee resources"):
        services["resource_master_commands"].create_resource(ResourceCreateCommand(name="External", worker_type=WorkerType.EXTERNAL, employee_id=employee.id))


def test_resource_desktop_dto_uses_current_platform_employee_profile(services):
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="DEP-DISPLAY", name="Display Department"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="EMP-DISPLAY", full_name="Original Name", department_id=department.id, email="before@example.com"))
    resource = services["resource_master_commands"].create_resource(ResourceCreateCommand(name="", worker_type=WorkerType.EMPLOYEE, employee_id=employee.id))
    services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, full_name="Current Name", email="after@example.com", expected_version=employee.version))
    view = build_detail_view_model(services["resource_query"].get_resource_summary(resource.id))
    assert view.title == "Current Name"
    assert view.state["contact"] == "after@example.com"
    assert view.state["employeeId"] == employee.id


def test_project_client_party_is_platform_owned_and_scope_checked(services):
    services['project_query']
    client = services["party_commands"].create_party(PartyCreateCommand(party_code="CUST-BOUNDARY", party_name="Client"))

    project = services['project_create'].create_project(ProjectCreateCommand(name="Party reference project", client_party_id=client.id))
    assert project.client_party_id == client.id

    services["party_commands"].deactivate_party(client.id)
    services['project_update'].update_project(ProjectUpdateCommand(project_id=project.id, name="Renamed project"))
    with pytest.raises(ValidationError, match="inactive"):
        services['project_create'].create_project(ProjectCreateCommand(name="New party link", client_party_id=client.id))
    with pytest.raises(ValidationError, match="not found"):
        services['project_create'].create_project(ProjectCreateCommand(name="Foreign party link", client_party_id="not-a-party"))


def test_project_department_reference_is_optional_and_platform_owned(services):
    services['project_query']
    project = services['project_create'].create_project(ProjectCreateCommand(name="No department project"))
    assert project.department_id is None

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="DEP-PROJECT", name="Project Department"))
    linked = services['project_create'].create_project(ProjectCreateCommand(name="Linked department project", department_id=department.id))
    assert linked.department_id == department.id
    services["department_commands"].deactivate_department(department.id)
    services['project_update'].update_project(ProjectUpdateCommand(project_id=linked.id, name="Historical department project"))
    with pytest.raises(ValidationError, match="inactive"):
        services['project_create'].create_project(ProjectCreateCommand(name="New department project", department_id=department.id))
    with pytest.raises(ValidationError, match="not found"):
        services['project_create'].create_project(ProjectCreateCommand(name="Unknown department project", department_id="not-a-department"))


def test_platform_master_data_and_composition_do_not_import_pm():
    root = Path(__file__).resolve().parents[4]
    paths = [root / "src/core/platform/infrastructure/composition/bootstrap.py"]
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
