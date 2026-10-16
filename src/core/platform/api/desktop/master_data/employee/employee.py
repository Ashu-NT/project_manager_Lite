from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
)
from src.core.platform.application.master_data.documents.dto.responses.document import (
    DocumentLinkDto,
    DocumentPageDto,
)
from src.core.platform.application.master_data.employee import (
    EmployeeCommandHandler,
    EmployeeDocumentCommandHandler,
    EmployeeQueryHandler,
)
from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.employee.dto.responses.employee import (
    EmployeeDto,
    EmployeePageDto,
)
from src.core.platform.application.master_data.org.dto.responses.organization import (
    OrganizationDto,
)
from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
    EmployeeDepartmentBreakdownRow,
    EmployeeHeadcountSummary,
    EmployeeSiteBreakdownRow,
)


class PlatformEmployeeDesktopApi:
    """Desktop-facing adapter for platform employee master data."""

    def __init__(
        self,
        *,
        employee_commands: EmployeeCommandHandler,
        employee_query: EmployeeQueryHandler,
        employee_documents: EmployeeDocumentCommandHandler,
    ) -> None:
        self._employee_commands = employee_commands
        self._employee_query = employee_query
        self._employee_documents = employee_documents

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: self._employee_query.get_context_organization()
        )

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[tuple[EmployeeDto, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                employee
                for employee in self._employee_query.list_employees(
                    active_only=active_only,
                    department_id=department_id,
                    site_id=site_id,
                )
            )
        )

    def list_employees_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> DesktopApiResult[EmployeePageDto]:
        return execute_desktop_operation(
            lambda: self._employee_query.list_employees_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    active_only=active_only,
                    department_id=department_id,
                    site_id=site_id,
                )
        )

    def get_headcount_summary(self) -> DesktopApiResult[EmployeeHeadcountSummary]:
        return execute_desktop_operation(
            lambda: self._employee_query.get_headcount_summary()
        )

    def get_department_breakdown(self) -> DesktopApiResult[tuple[EmployeeDepartmentBreakdownRow, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                row
                for row in self._employee_query.get_department_breakdown()
            )
        )

    def get_site_breakdown(self) -> DesktopApiResult[tuple[EmployeeSiteBreakdownRow, ...]]:
        return execute_desktop_operation(
            lambda: tuple(
                row
                for row in self._employee_query.get_site_breakdown()
            )
        )

    def create_employee(self, command: EmployeeCreateCommand) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.create_employee(command)
        )

    def update_employee(self, command: EmployeeUpdateCommand) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.update_employee(command)
        )

    def activate_employee(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.activate_employee(employee_id)
        )

    def deactivate_employee(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.deactivate_employee(employee_id)
        )

    def link_employee_user_account(self, employee_id: str, user_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.link_employee_user_account(employee_id, user_id)
        )

    def unlink_employee_user_account(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._employee_commands.unlink_employee_user_account(employee_id)
        )

    def list_employee_documents_page(
        self,
        employee_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        document_type: str | None = None,
    ) -> DesktopApiResult[DocumentPageDto]:
        return execute_desktop_operation(
            lambda: self._employee_query.list_employee_documents_page(
                    employee_id, page=page, page_size=page_size, search=search,
                    active_only=active_only, document_type=document_type,
                )
        )

    def link_employee_document(self, employee_id: str, document_id: str) -> DesktopApiResult[DocumentLinkDto]:
        return execute_desktop_operation(
            lambda: self._employee_documents.link_employee_document(employee_id, document_id)
        )

    def unlink_employee_document(self, employee_id: str, link_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._employee_documents.unlink_employee_document(employee_id, link_id)
        )










__all__ = ["PlatformEmployeeDesktopApi"]
