"""Employee.department_id is required (every Employee belongs to exactly
one Department), and a Department's Head of Department is simply an
Employee reference (employee.department_id == department.id) -- no
separate eligibility flag. These tests cover the invariants that keep that
reference consistent when the underlying Employee changes."""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError


def test_create_employee_requires_a_department(services) -> None:
    employee_service = services["employee_service"]
    with pytest.raises(ValidationError) as exc_info:
        employee_service.create_employee(employee_code="NODEPT-1", full_name="No Department")
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_REQUIRED"


def test_update_employee_cannot_clear_department(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    department = department_service.create_department(department_code="INV-DEPT-1", name="Dept One")
    employee = employee_service.create_employee(
        employee_code="INV-EMP-1", full_name="Cannot Clear", department_id=department.id
    )
    with pytest.raises(ValidationError) as exc_info:
        employee_service.update_employee(employee.id, department_id="", department="")
    assert exc_info.value.code == "EMPLOYEE_DEPARTMENT_REQUIRED"


def test_transferring_the_current_hod_to_another_department_is_rejected(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    department_a = department_service.create_department(department_code="INV-DEPT-A", name="Dept A")
    department_b = department_service.create_department(department_code="INV-DEPT-B", name="Dept B")
    hod = employee_service.create_employee(
        employee_code="INV-HOD-1", full_name="Current HOD", department_id=department_a.id
    )
    department_service.update_department(department_a.id, head_of_department_employee_id=hod.id)

    with pytest.raises(ValidationError) as exc_info:
        employee_service.update_employee(hod.id, department_id=department_b.id)
    assert exc_info.value.code == "EMPLOYEE_TRANSFER_BLOCKED_BY_HOD_ASSIGNMENT"

    # Clearing the HOD first unblocks the transfer.
    department_service.update_department(department_a.id, head_of_department_employee_id="")
    transferred = employee_service.update_employee(hod.id, department_id=department_b.id)
    assert transferred.department_id == department_b.id


def test_deactivating_the_current_hod_is_rejected(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    department = department_service.create_department(department_code="INV-DEPT-C", name="Dept C")
    hod = employee_service.create_employee(
        employee_code="INV-HOD-2", full_name="Deactivate Me", department_id=department.id
    )
    department_service.update_department(department.id, head_of_department_employee_id=hod.id)

    with pytest.raises(ValidationError) as exc_info:
        employee_service.update_employee(hod.id, is_active=False)
    assert exc_info.value.code == "EMPLOYEE_DEACTIVATION_BLOCKED_BY_HOD_ASSIGNMENT"

    # Clearing the HOD first unblocks deactivation.
    department_service.update_department(department.id, head_of_department_employee_id="")
    deactivated = employee_service.update_employee(hod.id, is_active=False)
    assert deactivated.is_active is False


def test_deactivating_an_ordinary_employee_who_is_not_hod_of_anything_succeeds(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    department = department_service.create_department(department_code="INV-DEPT-D", name="Dept D")
    employee = employee_service.create_employee(
        employee_code="INV-EMP-2", full_name="Ordinary Employee", department_id=department.id
    )
    deactivated = employee_service.update_employee(employee.id, is_active=False)
    assert deactivated.is_active is False


def test_transferring_an_employee_who_is_not_hod_of_anything_succeeds(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    department_a = department_service.create_department(department_code="INV-DEPT-E", name="Dept E")
    department_b = department_service.create_department(department_code="INV-DEPT-F", name="Dept F")
    employee = employee_service.create_employee(
        employee_code="INV-EMP-3", full_name="Movable Employee", department_id=department_a.id
    )
    moved = employee_service.update_employee(employee.id, department_id=department_b.id)
    assert moved.department_id == department_b.id
