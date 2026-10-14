from __future__ import annotations

from src.core.platform.api.desktop.master_data.department.models.department import (
    DepartmentDto,
    DepartmentPageDto,
    DepartmentRollupSummaryDto,
)
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.domain.master_data.department import Department


class PlatformDepartmentDesktopApi:
    """Desktop-facing adapter for platform department master data."""

    def __init__(
        self,
        *,
        department_commands: DepartmentCommandHandler,
        department_query: DepartmentQueryHandler,
    ) -> None:
        self._department_commands = department_commands
        self._department_query = department_query

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._department_query.get_context_organization())
        )

    def list_departments(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[tuple[DepartmentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                self._serialize_department(department)
                for department in self._department_query.list_departments(
                    active_only=active_only, site_id=site_id
                )
            )
        )

    def get_department_rollup_summary(self) -> DesktopApiResult[DepartmentRollupSummaryDto]:
        return execute_desktop_operation(
            lambda: self._serialize_rollup_summary(
                self._department_query.get_department_rollup_summary()
            )
        )

    def list_departments_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[DepartmentPageDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department_page(
                self._department_query.list_departments_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    site_id=site_id,
                )
            )
        )

    def create_department(self, command: DepartmentCreateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(
                self._department_commands.create_department(command)
            )
        )

    def update_department(self, command: DepartmentUpdateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(
                self._department_commands.update_department(command)
            )
        )

    def activate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(self._department_commands.activate_department(department_id))
        )

    def deactivate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._serialize_department(self._department_commands.deactivate_department(department_id))
        )

    def _serialize_department_page(self, page) -> DepartmentPageDto:
        return DepartmentPageDto(
            items=tuple(self._serialize_department(department) for department in page.items),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
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
            head_of_department_employee_id=department.head_of_department_employee_id,
            is_active=department.is_active,
            notes=department.notes,
            version=department.version,
            created_at=department.created_at,
            updated_at=department.updated_at,
        )

__all__ = ["PlatformDepartmentDesktopApi"]
