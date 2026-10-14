from __future__ import annotations

import pytest

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.domain.enums import WorkerType
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.use_cases.master_data.department.commands import (
    DepartmentCreateCommand,
)
from src.core.platform.contract.use_cases.master_data.employee.commands import (
    EmployeeCreateCommand,
)


def test_project_manager_uses_eligible_user_identity_not_resource_id(services) -> None:
    project_service = services["project_service"]
    user_id = services["user_session"].principal.user_id
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="PM-MANAGER", name="Management"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="PM-MANAGER", full_name="Manager Employee", department_id=department.id))
    services["employee_commands"].link_employee_user_account(employee.id, user_id)
    resource = services["resource_master_commands"].create_resource(
        name="Manager Resource", worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    assert user_id != resource.id

    candidates = services["project_query"].list_eligible_manager_candidates()
    assert any(row.user_id == user_id and row.display_name == "Manager Employee" for row in candidates)
    assert all(row.user_id != resource.id for row in candidates)
    options = ProjectManagementProjectsDesktopApi(
        project_service=project_service,
        project_query=services["project_query"],
    ).list_manager_candidates()
    assert any(row.user_id == user_id for row in options)

    project = project_service.create_project("Eligible Manager", manager_user_id=user_id)
    assert project.manager_user_id == user_id
    with pytest.raises(ValidationError) as create_error:
        project_service.create_project("Resource Is Not User", manager_user_id=resource.id)
    assert create_error.value.code == "PROJECT_MANAGER_NOT_ELIGIBLE"

    other = project_service.create_project("Manager Update")
    with pytest.raises(ValidationError) as update_error:
        project_service.update_project(other.id, manager_user_id=resource.id)
    assert update_error.value.code == "PROJECT_MANAGER_NOT_ELIGIBLE"
    updated = project_service.update_project(other.id, manager_user_id=user_id)
    assert updated.manager_user_id == user_id

    services["resource_master_commands"].deactivate_resource(
        resource_id=resource.id, expected_version=resource.version
    )
    assert all(
        row.user_id != user_id
        for row in services["project_query"].list_eligible_manager_candidates()
    )
    with pytest.raises(ValidationError) as inactive_error:
        project_service.create_project("Inactive Manager Resource", manager_user_id=user_id)
    assert inactive_error.value.code == "PROJECT_MANAGER_NOT_ELIGIBLE"


def test_project_manager_rejects_unregistered_user(services) -> None:
    user = services["user_registration"].onboard_tenant_user(
        username="pm-no-resource", raw_password="StrongPass123!"
    )
    with pytest.raises(ValidationError) as error:
        services["project_service"].create_project(
            "Unregistered Manager", manager_user_id=user.id
        )
    assert error.value.code == "PROJECT_MANAGER_NOT_ELIGIBLE"
