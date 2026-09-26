from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.core.platform.access.authorization import filter_scope_rows
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.contract.uow.department_unit_of_work import (
    DepartmentUnitOfWorkFactory,
)
from src.core.platform.domain.master_data.department import Department
from src.core.platform.domain.master_data.org import Organization
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

from . import department_commands as _cmd
from . import department_queries as _queries
from .department_access import require_department_read_access
from .department_context import active_organization

_DEFAULT_DEPARTMENT_PAGE_SIZE = 25
DEPARTMENT_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)


@dataclass(frozen=True)
class DepartmentPage:
    items: list[Department] = field(default_factory=list)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = _DEFAULT_DEPARTMENT_PAGE_SIZE


class DepartmentService:
    def __init__(
        self,
        session: Session,
        department_repo: DepartmentRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        user_session=None,
        enterprise_audit_service=None,
        tenant_context_service: TenantContextService | None = None,
        overview_rollup_reader: PlatformOverviewRollupReader | None = None,
        uow_factory: DepartmentUnitOfWorkFactory,
        clock: Clock,
    ):
        self._session = session
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._employee_repo = employee_repo
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._tenant_context_service = tenant_context_service
        self._overview_rollup_reader = overview_rollup_reader
        self._uow_factory = uow_factory
        self._clock = clock

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def list_departments(
        self, *, active_only: bool | None = None, site_id: str | None = None
    ) -> list[Department]:
        return _queries.list_departments(self, active_only=active_only, site_id=site_id)

    def get_department_rollup_summary(self) -> DepartmentRollupSummary:
        require_department_read_access(self, "view department rollup summary")
        organization = active_organization(self)
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="view department rollup summary",
        )
        if self._overview_rollup_reader is None:
            raise RuntimeError("Platform overview rollup reader is not configured.")
        return self._overview_rollup_reader.get_department_summary(
            organization_id=organization.id,
            tenant_id=tenant_id,
        )

    def list_departments_page_for_organization(
        self,
        organization_id: str,
        *,
        page: int = 1,
        page_size: int = _DEFAULT_DEPARTMENT_PAGE_SIZE,
        search: str = "",
        active_only: bool | None = None,
        site_id: str | None = None,
    ) -> DepartmentPage:
        """Tenant-scoped read for ANY organization in the caller's tenant --
        unlike list_departments()/search_departments(), not limited to the
        session's active organization. For Organization Detail's
        Departments tab, where an admin may be viewing an organization they
        haven't switched into.

        Read-only: never used by create/update/delete, which keep using
        active_organization(self) (the existing, unchanged domain rule).
        Never gates on the organization's own lifecycle status -- inactive
        and archived organizations' department history remains readable
        here.
        """
        require_department_read_access(self, "list departments")
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Tenant context is required to list departments.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="list departments for organization"
        )
        target_organization = self._organization_repo.get_for_tenant(organization_id, tenant_id)
        if target_organization is None:
            raise NotFoundError(
                "Organization not found in the current tenant.",
                code="ORGANIZATION_NOT_FOUND",
            )
        normalized_page = max(1, page)
        normalized_page_size = (
            page_size if page_size in DEPARTMENT_PAGE_SIZE_OPTIONS else _DEFAULT_DEPARTMENT_PAGE_SIZE
        )
        items, total, filtered_total = self._department_repo.list_page_for_organization_in_tenant(
            organization_id,
            tenant_id,
            page=normalized_page,
            page_size=normalized_page_size,
            search=search,
            active_only=active_only,
            site_id=site_id,
        )
        items = filter_scope_rows(
            items,
            self._user_session,
            scope_type="department",
            permission_code="department.read",
            scope_id_getter=lambda row: getattr(row, "id", ""),
        )
        return DepartmentPage(
            items=items,
            total=total,
            filtered_total=filtered_total,
            page=normalized_page,
            page_size=normalized_page_size,
        )

    def search_departments(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Department]:
        return _queries.search_departments(self, search_text=search_text, active_only=active_only)

    def get_department(self, department_id: str) -> Department:
        return _queries.get_department(self, department_id)

    def find_department_by_code(self, department_code: str) -> Department | None:
        return _queries.find_department_by_code(self, department_code)

    def get_context_organization(self) -> Organization:
        return _queries.get_context_organization(self)

    def create_department(
        self,
        *,
        department_code: str,
        name: str | None = None,
        display_name: str | None = None,
        description: str = "",
        site_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str = "",
        cost_center_code: str = "",
        head_of_department_employee_id: str | None = None,
        notes: str = "",
    ) -> Department:
        return _cmd.create_department(
            self,
            department_code=department_code,
            name=name,
            display_name=display_name,
            description=description,
            site_id=site_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            head_of_department_employee_id=head_of_department_employee_id,
            notes=notes,
        )

    def update_department(
        self,
        department_id: str,
        *,
        department_code: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        site_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str | None = None,
        cost_center_code: str | None = None,
        head_of_department_employee_id: str | None = None,
        notes: str | None = None,
        expected_version: int | None = None,
    ) -> Department:
        return _cmd.update_department(
            self,
            department_id,
            department_code=department_code,
            name=name,
            display_name=display_name,
            description=description,
            site_id=site_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            head_of_department_employee_id=head_of_department_employee_id,
            notes=notes,
            expected_version=expected_version,
        )

    def activate_department(self, department_id: str) -> Department:
        return _cmd.activate_department(self, department_id)

    def deactivate_department(self, department_id: str) -> Department:
        return _cmd.deactivate_department(self, department_id)


__all__ = ["DEPARTMENT_PAGE_SIZE_OPTIONS", "DepartmentPage", "DepartmentService"]
