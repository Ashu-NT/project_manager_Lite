from __future__ import annotations

from src.core.platform.api.desktop.master_data.documents.models.document import (
    DocumentDto,
    DocumentPageDto,
    DocumentLinkDto,
)
from src.core.platform.api.desktop.master_data.employee.models.employee import (
    EmployeeCreateCommand,
    EmployeeDepartmentBreakdownRowDto,
    EmployeeDto,
    EmployeeHeadcountSummaryDto,
    EmployeePageDto,
    EmployeeSiteBreakdownRowDto,
    EmployeeUpdateCommand,
)
from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationDto,
)
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.api.desktop.support._support import (
    execute_desktop_operation,
    serialize_organization,
)
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)


class PlatformEmployeeDesktopApi:
    """Desktop-facing adapter for platform employee master data."""

    def __init__(self, *, employee_service: EmployeeService) -> None:
        self._employee_service = employee_service

    def get_context(self) -> DesktopApiResult[OrganizationDto]:
        return execute_desktop_operation(
            lambda: serialize_organization(self._employee_service.get_context_organization())
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
                self._serialize_employee(employee)
                for employee in self._employee_service.list_employees(
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
            lambda: self._serialize_employee_page(
                self._employee_service.list_employees_page_for_organization(
                    organization_id,
                    page=page,
                    page_size=page_size,
                    search=search,
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
                    expected_version=command.expected_version,
                )
            )
        )

    def activate_employee(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(self._employee_service.activate_employee(employee_id))
        )

    def deactivate_employee(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(self._employee_service.deactivate_employee(employee_id))
        )

    def link_employee_user_account(self, employee_id: str, user_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(
                self._employee_service.link_employee_user_account(employee_id, user_id)
            )
        )

    def unlink_employee_user_account(self, employee_id: str) -> DesktopApiResult[EmployeeDto]:
        return execute_desktop_operation(
            lambda: self._serialize_employee(
                self._employee_service.unlink_employee_user_account(employee_id)
            )
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
            lambda: self._serialize_document_page(
                self._employee_service.list_employee_documents_page(
                    employee_id, page=page, page_size=page_size, search=search,
                    active_only=active_only, document_type=document_type,
                )
            )
        )

    def link_employee_document(self, employee_id: str, document_id: str) -> DesktopApiResult[DocumentLinkDto]:
        return execute_desktop_operation(
            lambda: self._serialize_document_link(
                self._employee_service.link_employee_document(employee_id, document_id)
            )
        )

    def unlink_employee_document(self, employee_id: str, link_id: str) -> DesktopApiResult[None]:
        return execute_desktop_operation(
            lambda: self._employee_service.unlink_employee_document(employee_id, link_id)
        )

    def _serialize_document_page(self, page) -> DocumentPageDto:
        return DocumentPageDto(
            items=tuple(
                self._serialize_document(row.document, link_id=row.link.id) for row in page.items
            ),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
        )

    @staticmethod
    def _serialize_document(document, *, link_id: str = "") -> DocumentDto:
        return DocumentDto(
            id=document.id,
            organization_id=document.organization_id,
            document_code=document.document_code,
            title=document.title,
            document_type=document.document_type,
            document_structure_id=document.document_structure_id,
            storage_kind=document.storage_kind,
            storage_uri=document.storage_uri,
            file_name=document.file_name,
            mime_type=document.mime_type,
            source_system=document.source_system,
            uploaded_at=document.uploaded_at,
            uploaded_by_user_id=document.uploaded_by_user_id,
            effective_date=document.effective_date,
            review_date=document.review_date,
            confidentiality_level=document.confidentiality_level,
            business_version_label=document.business_version_label,
            is_current=document.is_current,
            notes=document.notes,
            is_active=document.is_active,
            version=document.version,
            link_id=link_id,
        )

    @staticmethod
    def _serialize_document_link(link) -> DocumentLinkDto:
        return DocumentLinkDto(
            id=link.id,
            organization_id=link.organization_id,
            document_id=link.document_id,
            module_code=link.module_code,
            entity_type=link.entity_type,
            entity_id=link.entity_id,
            link_role=link.link_role,
        )

    def _serialize_employee_page(self, page) -> EmployeePageDto:
        return EmployeePageDto(
            items=tuple(self._serialize_employee(employee) for employee in page.items),
            total=page.total,
            filtered_total=page.filtered_total,
            page=page.page,
            page_size=page.page_size,
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
            status=employee.status.value,
            is_active=employee.is_active,
            user_id=employee.user_id,
            version=employee.version,
            organization_id=employee.organization_id,
        )


__all__ = ["PlatformEmployeeDesktopApi"]
