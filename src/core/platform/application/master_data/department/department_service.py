from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.read.overview.platform_overview_rollup_reader import (
    DepartmentRollupSummary,
    PlatformOverviewRollupReader,
)
from src.core.platform.contract.repositories.master_data.department.contracts import DepartmentRepository
from src.core.platform.contract.uow.department_unit_of_work import DepartmentUnitOfWorkFactory
from src.core.platform.domain.master_data.department import Department
from src.core.platform.contract.repositories.master_data.employee.contracts import EmployeeRepository
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

from .department_access import require_department_read_access
from .department_context import active_organization
from . import department_commands as _cmd
from . import department_queries as _queries


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

    def list_departments(self, *, active_only: bool | None = None) -> list[Department]:
        return _queries.list_departments(self, active_only=active_only)

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
        manager_employee_id: str | None = None,
        is_active: bool = True,
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
            manager_employee_id=manager_employee_id,
            is_active=is_active,
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
        manager_employee_id: str | None = None,
        is_active: bool | None = None,
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
            manager_employee_id=manager_employee_id,
            is_active=is_active,
            notes=notes,
            expected_version=expected_version,
        )


__all__ = ["DepartmentService"]
