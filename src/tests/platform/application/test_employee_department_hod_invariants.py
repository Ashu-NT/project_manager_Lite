"""Employee.department_id is required (every Employee belongs to exactly
one Department), and a Department's Head of Department is simply an
Employee reference (employee.department_id == department.id) -- no
separate eligibility flag. These tests cover the invariants that keep that
reference consistent when the underlying Employee changes."""

from __future__ import annotations

import pytest

from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.employee.dto import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.common.exceptions import ValidationError


def test_create_employee_requires_a_department(services) -> None:
    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="NODEPT-1", full_name="No Department"))
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_REQUIRED"


def test_update_employee_cannot_clear_department(services) -> None:
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-1", name="Dept One"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="INV-EMP-1", full_name="Cannot Clear", department_id=department.id))
    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, department_id="", department=""))
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_REQUIRED"


def test_transferring_the_current_hod_to_another_department_is_rejected(services) -> None:

    department_a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-A", name="Dept A"))
    department_b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-B", name="Dept B"))
    hod = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="INV-HOD-1", full_name="Current HOD", department_id=department_a.id))
    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department_a.id, head_of_department_employee_id=hod.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=hod.id, department_id=department_b.id))
    assert exc_info.value.code == "EMPLOYEE_TRANSFER_BLOCKED_BY_HOD_ASSIGNMENT"

    # Clearing the HOD first unblocks the transfer.
    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department_a.id, head_of_department_employee_id=""))
    transferred = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=hod.id, department_id=department_b.id))
    assert transferred.department_id == department_b.id


def test_deactivating_the_current_hod_is_rejected(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-C", name="Dept C"))
    hod = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="INV-HOD-2", full_name="Deactivate Me", department_id=department.id))
    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=hod.id))

    with pytest.raises(ValidationError) as exc_info:
        services["employee_commands"].deactivate_employee(hod.id)
    assert exc_info.value.code == "EMPLOYEE_DEACTIVATION_BLOCKED_BY_HOD_ASSIGNMENT"

    # Clearing the HOD first unblocks deactivation.
    services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=""))
    deactivated = services["employee_commands"].deactivate_employee(hod.id)
    assert deactivated.is_active is False


def test_deactivating_an_ordinary_employee_who_is_not_hod_of_anything_succeeds(services) -> None:

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-D", name="Dept D"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="INV-EMP-2", full_name="Ordinary Employee", department_id=department.id))
    deactivated = services["employee_commands"].deactivate_employee(employee.id)
    assert deactivated.is_active is False


def test_transferring_an_employee_who_is_not_hod_of_anything_succeeds(services) -> None:

    department_a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-E", name="Dept E"))
    department_b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="INV-DEPT-F", name="Dept F"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="INV-EMP-3", full_name="Movable Employee", department_id=department_a.id))
    moved = services["employee_commands"].update_employee(EmployeeUpdateCommand(employee_id=employee.id, department_id=department_b.id))
    assert moved.department_id == department_b.id
