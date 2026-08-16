from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.master_data.employee.models.employee import (
    EmployeeCreateCommand,
    EmployeeDepartmentBreakdownRowDto,
    EmployeeDto,
    EmployeeHeadcountSummaryDto,
    EmployeeSiteBreakdownRowDto,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.employee.employee_service import EmployeeService


class PlatformEmployeeDesktopApi:
    """Desktop-facing adapter for platform employee master data."""

    def __init__(self, *, employee_service: EmployeeService) -> None:
        self._employee_service = employee_service

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[tuple[EmployeeDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_employee(employee)
                for employee in self._employee_service.list_employees(
                    active_only=active_only,
                    department_id=department_id,
                    site_id=site_id,
                )
            )
        )

    def get_headcount_summary(self) -> DesktopApiResult[EmployeeHeadcountSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_headcount_summary(
                self._employee_service.get_headcount_summary()
            )
        )

    def get_department_breakdown(self) -> DesktopApiResult[tuple[EmployeeDepartmentBreakdownRowDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_department_breakdown_row(row)
                for row in self._employee_service.get_department_breakdown()
            )
        )

    def get_site_breakdown(self) -> DesktopApiResult[tuple[EmployeeSiteBreakdownRowDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_site_breakdown_row(row)
                for row in self._employee_service.get_site_breakdown()
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
                    user_id=command.user_id,
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
                    user_id=command.user_id,
                    expected_version=command.expected_version,
                )
            )
        )

    @staticmethod
    def _serialize_headcount_summary(summary) -> EmployeeHeadcountSummaryDto:
        return EmployeeHeadcountSummaryDto(total=summary.total, active=summary.active)

    @staticmethod
    def _serialize_department_breakdown_row(row) -> EmployeeDepartmentBreakdownRowDto:
        return EmployeeDepartmentBreakdownRowDto(
            department_id=row.department_id,
            department_name=row.department_name,
            total=row.total,
            active=row.active,
        )

    @staticmethod
    def _serialize_site_breakdown_row(row) -> EmployeeSiteBreakdownRowDto:
        return EmployeeSiteBreakdownRowDto(
            site_id=row.site_id,
            site_name=row.site_name,
            total=row.total,
            active=row.active,
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
            user_id=employee.user_id,
            version=employee.version,
        )


__all__ = ["PlatformEmployeeDesktopApi"]
