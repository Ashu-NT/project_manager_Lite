from __future__ import annotations

from src.core.platform.api.desktop.support._support import execute_desktop_operation, serialize_organization
from src.core.platform.api.desktop.master_data.org.models.organization import OrganizationDto
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.master_data.department.models.department import (
    DepartmentCreateCommand,
    DepartmentDto,
    DepartmentRollupSummaryDto,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.department.department_service import DepartmentService
from src.core.platform.domain.master_data.department import Department

class PlatformDepartmentDesktopApi:
    """Desktop-facing adapter for platform department master data."""

    def __init__(self, *, department_service: DepartmentService) -> None:
        self._department_service = department_service

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._department_service.get_context_organization())
        )

    def list_departments(
        self,
        *,
        active_only: bool | None = None,
    ) -> DesktopApiResult[tuple[DepartmentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_department(department)
                for department in self._department_service.list_departments(active_only=active_only)
            )
        )

    def get_department_rollup_summary(self) -> DesktopApiResult[DepartmentRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_rollup_summary(
                self._department_service.get_department_rollup_summary()
            )
        )

    def create_department(self, command: DepartmentCreateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(
                self._department_service.create_department(
                    department_code=command.department_code,
                    name=command.name,
                    description=command.description,
                    site_id=command.site_id,
                    parent_department_id=command.parent_department_id,
                    department_type=command.department_type,
                    cost_center_code=command.cost_center_code,
                    manager_employee_id=command.manager_employee_id,
                    is_active=command.is_active,
                    notes=command.notes,
                )
            )
        )

    def update_department(self, command: DepartmentUpdateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(
                self._department_service.update_department(
                    command.department_id,
                    department_code=command.department_code,
                    name=command.name,
                    description=command.description,
                    site_id=command.site_id,
                    parent_department_id=command.parent_department_id,
                    department_type=command.department_type,
                    cost_center_code=command.cost_center_code,
                    manager_employee_id=command.manager_employee_id,
                    is_active=command.is_active,
                    notes=command.notes,
                    expected_version=command.expected_version,
                )
            )
        )

    @staticmethod
    def _serialize_rollup_summary(summary) -> DepartmentRollupSummaryDto:
        return DepartmentRollupSummaryDto(total=summary.total, active=summary.active)

    @staticmethod
    def _serialize_department(department: Department) -> DepartmentDto:
        return DepartmentDto(
            id=department.id,
            organization_id=department.organization_id,
            department_code=department.department_code,
            name=department.name,
            description=department.description,
            site_id=department.site_id,
            parent_department_id=department.parent_department_id,
            department_type=department.department_type,
            cost_center_code=department.cost_center_code,
            manager_employee_id=department.manager_employee_id,
            is_active=department.is_active,
            notes=department.notes,
            version=department.version,
        )

__all__ = ["PlatformDepartmentDesktopApi"]
