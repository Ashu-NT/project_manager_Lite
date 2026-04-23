from __future__ import annotations

from src.api.desktop.platform._support import execute_desktop_operation
from src.api.desktop.platform.models import (
    DesktopApiResult,
    EmployeeCreateCommand,
    EmployeeDto,
    EmployeeUpdateCommand,
)
from src.core.platform.org import EmployeeService


class PlatformEmployeeDesktopApi:
    """Desktop-facing adapter for platform employee master data."""

    def __init__(self, *, employee_service: EmployeeService) -> None:
        self._employee_service = employee_service

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[EmployeeDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_employee(employee)
                for employee in self._employee_service.list_employees(active_only=active_only)
            )
        )

    def create_employee(self, command: EmployeeCreateCommand) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(
                self._employee_service.create_employee(
                    employee_code=command.employee_code,
                    full_name=command.full_name,
                    department_id=command.department_id,
                    department=command.department,
                    site_id=command.site_id,
                    site_name=command.site_name,
                    title=command.title,
                    employment_type=command.employment_type,
                    email=command.email,
                    phone=command.phone,
                    is_active=command.is_active,
                )
            )
        )

    def update_employee(self, command: EmployeeUpdateCommand) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(
                self._employee_service.update_employee(
                    command.employee_id,
                    employee_code=command.employee_code,
                    full_name=command.full_name,
                    department_id=command.department_id,
                    department=command.department,
                    site_id=command.site_id,
                    site_name=command.site_name,
                    title=command.title,
                    employment_type=command.employment_type,
                    email=command.email,
                    phone=command.phone,
                    is_active=command.is_active,
                    expected_version=command.expected_version,
                )
            )
        )

    @staticmethod
    def _serialize_employee(employee) -> EmployeeDto:
        return EmployeeDto(
            id=employee.id,
            employee_code=employee.employee_code,
            full_name=employee.full_name,
            department_id=employee.department_id,
            department=employee.department,
            site_id=employee.site_id,
            site_name=employee.site_name,
            title=employee.title,
            employment_type=employee.employment_type.value,
            email=employee.email,
            phone=employee.phone,
            is_active=employee.is_active,
            version=employee.version,
        )


__all__ = ["PlatformEmployeeDesktopApi"]
