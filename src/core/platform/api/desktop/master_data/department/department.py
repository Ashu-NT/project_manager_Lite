from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.department.dto.commands.department import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.department.dto.responses.department import (
    DepartmentDto,
    DepartmentPageDto,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
)


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
            lambda: self._department_query.get_context_organization()
        )

    def list_departments(
        self,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[tuple[DepartmentDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                department
                for department in self._department_query.list_departments(
                    active_only=active_only, site_id=site_id
                )
            )
        )

    def get_department_rollup_summary(self) -> DesktopApiResult[DepartmentRollupSummary]:
        return execute_desktop_operation(
            lambda: self._department_query.get_department_rollup_summary()
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
            lambda: self._department_query.list_departments_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    site_id=site_id,
                )
        )

    def create_department(self, command: DepartmentCreateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._department_commands.create_department(command)
        )

    def update_department(self, command: DepartmentUpdateCommand) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._department_commands.update_department(command)
        )

    def activate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._department_commands.activate_department(department_id)
        )

    def deactivate_department(self, department_id: str) -> DesktopApiResult[DepartmentDto]:
        return execute_desktop_operation(
            lambda: self._department_commands.deactivate_department(department_id)
        )




__all__ = ["PlatformDepartmentDesktopApi"]
