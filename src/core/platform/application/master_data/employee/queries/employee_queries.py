from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.platform.application.master_data.documents.queries.document_queries import (
    DocumentQueryHandler,
)
from src.core.platform.application.master_data.employee.employee_context import (
    active_organization_id,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    DOCUMENT_VIEW_PERMISSION as _DOCUMENT_VIEW_PERMISSION,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    ENTITY_TYPE as _ENTITY_TYPE,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    MODULE_CODE as _MODULE_CODE,
)
from src.core.platform.application.master_data.employee.employee_document_access import (
    require_employee_in_context,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.core.platform.application.master_data.documents.queries.document_queries import (
        EntityDocumentPage,
    )
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.contract.repositories.master_data.employee.contracts import (
        EmployeeRepository,
    )

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    ValidationError,
)
from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
    EmployeeDepartmentBreakdownRow,
    EmployeeHeadcountReader,
    EmployeeHeadcountSummary,
    EmployeeSiteBreakdownRow,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.domain.master_data.employee import Employee
from src.core.platform.domain.master_data.org import Organization

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext


_DEFAULT_EMPLOYEE_PAGE_SIZE = 25
EMPLOYEE_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class EmployeePage:
    items: list[Employee] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_EMPLOYEE_PAGE_SIZE


class EmployeeQueryHandler:
    """Employee reads: active-organization lists and lookups, headcount and
    department/site breakdowns, and the tenant-scoped page for any organization."""

    def __init__(
        self,
        *,
        employee_repo: EmployeeRepository,
        organization_repo: OrganizationRepository | None,
        headcount_reader: EmployeeHeadcountReader | None,
        document_query: DocumentQueryHandler,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._employee_repo = employee_repo
        self._organization_repo = organization_repo
        self._headcount_reader = headcount_reader
        self._document_query = document_query
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> list[Employee]:
        require_permission(self._user_session, "employee.read", operation_label="list employees")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="list employees")
        return self._employee_repo.list_for_organization(
            organization_id,
            active_only=active_only,
            department_id=department_id,
            site_id=site_id,
        )

    def list_employees_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_EMPLOYEE_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> EmployeePage:
        """Tenant-scoped read for ANY organization in the caller's tenant --
        unlike list_employees(), not limited to the session's active
        organization. For Organization Detail's Employees tab, where an
        admin may be viewing an organization they haven't switched into.

        Read-only: never used by create/update/delete, which keep using
        active_organization_id(self._tenant_context_service, ) (the existing, unchanged domain
        rule). Never gates on the organization's own lifecycle status --
        inactive and archived organizations' employee history remains
        readable here. Mirrors list_employees()'s own permission check
        (plain employee.read, no scope-row filtering -- Employee has none
        today, unlike Site/Department).
        """
        require_permission(
            self._user_session, "employee.read", operation_label="list employees for organization"
        )
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        if self._organization_repo is None:
            raise RuntimeError("Organization repository is not configured.")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list employees for organization"
        )
        target_organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if target_organization is None:
            raise NotFoundError(
                "Organization not found in the current tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in EMPLOYEE_PAGE_SIZE_OPTIONS else _DEFAULT_EMPLOYEE_PAGE_SIZE
        )
        items, total, filtered_total = self._employee_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            active_only=active_only,
            department_id=department_id,
            site_id=site_id,
        )
        return EmployeePage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

    def get_headcount_summary(self) -> EmployeeHeadcountSummary:
        require_permission(
            self._user_session, "employee.read", operation_label="view employee headcount summary"
        )
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        if self._headcount_reader is None:
            raise RuntimeError("Employee headcount reader is not configured.")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view employee headcount summary",
        )
        organization_id = active_organization_id(self._tenant_context_service, 
            operation_label="view employee headcount summary"
        )
        return self._headcount_reader.get_summary(
            tenant_id=tenant_id, organization_id=organization_id
        )

    def get_department_breakdown(self) -> tuple[EmployeeDepartmentBreakdownRow, ...]:
        require_permission(
            self._user_session, "employee.read", operation_label="view employee department breakdown"
        )
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        if self._headcount_reader is None:
            raise RuntimeError("Employee headcount reader is not configured.")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view employee department breakdown",
        )
        organization_id = active_organization_id(self._tenant_context_service, 
            operation_label="view employee department breakdown"
        )
        return self._headcount_reader.get_department_breakdown(
            tenant_id=tenant_id, organization_id=organization_id
        )

    def get_site_breakdown(self) -> tuple[EmployeeSiteBreakdownRow, ...]:
        require_permission(
            self._user_session, "employee.read", operation_label="view employee site breakdown"
        )
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        if self._headcount_reader is None:
            raise RuntimeError("Employee headcount reader is not configured.")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view employee site breakdown",
        )
        organization_id = active_organization_id(self._tenant_context_service, 
            operation_label="view employee site breakdown"
        )
        return self._headcount_reader.get_site_breakdown(
            tenant_id=tenant_id, organization_id=organization_id
        )

    def get_employee(self, employee_id: str) -> Employee:
        require_permission(self._user_session, "employee.read", operation_label="view employee")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="view employee")
        employee = self._employee_repo.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        return employee

    def get_context_organization(self) -> Organization:
        """The caller's active Organization, for the standalone Employees
        workspace's breadcrumb/subtitle -- mirrors DepartmentQueryHandler's own
        get_context_organization() exactly."""
        require_permission(self._user_session, "employee.read", operation_label="view employee context")
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        organization = self._tenant_context_service.get_active_organization()
        if organization is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return organization

    def list_employee_documents_page(
        self,
        employee_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        active_only: bool | None = None,
        document_type: str | None = None,
    ) -> EntityDocumentPage:
        require_permission(self._user_session, "employee.read", operation_label="list employee documents")
        require_permission(self._user_session, _DOCUMENT_VIEW_PERMISSION, operation_label="list employee documents")
        require_employee_in_context(self._employee_repo, self._tenant_context_service, employee_id)
        return self._document_query.list_documents_page_for_entity(
            module_code=_MODULE_CODE,
            entity_type=_ENTITY_TYPE,
            entity_id=employee_id,
            page=page,
            page_size=page_size,
            search=search,
            active_only=active_only,
            document_type=document_type,
        )


__all__ = ["EMPLOYEE_PAGE_SIZE_OPTIONS", "EmployeePage", "EmployeeQueryHandler"]
