from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.master_data.employee.employee_support import (
    resolve_employee_department_reference,
    resolve_employee_site_reference,
    sync_linked_employee_resources,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.interface.master_data.employee.contracts import (
    ResourceMasterEventFactory,
)
from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
    EmployeeDepartmentBreakdownRow,
    EmployeeHeadcountReader,
    EmployeeHeadcountSummary,
    EmployeeSiteBreakdownRow,
)
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
    LinkedEmployeeResourceRepository,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.contract.uow.employee_unit_of_work import (
    EmployeeUnitOfWorkFactory,
)
from src.core.platform.domain.master_data.employee import Employee, EmploymentType
from src.core.platform.domain.master_data.employee.events import (
    EmployeeCreated,
    EmployeeProfileUpdated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )
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


class EmployeeService:
    def __init__(
        self,
        session: Session,
        employee_repo: EmployeeRepository,
        *,
        resource_repo: LinkedEmployeeResourceRepository | None = None,
        site_repo: SiteRepository | None = None,
        department_repo: DepartmentRepository | None = None,
        organization_repo: OrganizationRepository | None = None,
        tenant_context_service: TenantContextService | None = None,
        user_session: UserSessionContext | None = None,
        enterprise_audit_service: EnterpriseAuditService | None = None,
        headcount_reader: EmployeeHeadcountReader | None = None,
        resource_master_event_factory: ResourceMasterEventFactory | None = None,
        uow_factory: EmployeeUnitOfWorkFactory,
        clock: Clock,
    ):
        self._session = session
        self._employee_repo = employee_repo
        self._resource_repo = resource_repo
        self._site_repo = site_repo
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._headcount_reader = headcount_reader
        self._resource_master_event_factory = resource_master_event_factory
        self._uow_factory = uow_factory
        self._clock = clock
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def create_employee(
        self,
        *,
        employee_code: str,
        full_name: str,
        department_id: str | None = None,
        department: str = "",
        site_id: str | None = None,
        site_name: str = "",
        title: str = "",
        employment_type: EmploymentType | str = EmploymentType.FULL_TIME,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
        user_id: str | None = None,
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="create employee")
        organization_id = self._active_organization_id(operation_label="create employee")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="create employee"
        )
        employee = Employee.create(
            employee_code=employee_code,
            full_name=full_name,
            organization_id=organization_id,
            department_id=department_id,
            department=department,
            site_id=site_id,
            site_name=site_name,
            title=title,
            employment_type=employment_type,
            email=email,
            phone=phone,
            is_active=bool(is_active),
            user_id=user_id,
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            if uow.employees.get_by_code_for_organization(employee.employee_code, organization_id) is not None:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")
            employee.department_id, employee.department = resolve_employee_department_reference(
                department_repo=uow.departments,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                department_id=employee.department_id,
                department_name=employee.department,
            )
            employee.site_id, employee.site_name = resolve_employee_site_reference(
                site_repo=uow.sites,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                site_id=employee.site_id,
                site_name=employee.site_name,
            )
            try:
                uow.employees.add(employee)
                record_audit_entry(
                    uow,
                    operation="create",
                    entity_type="employee",
                    entity_id=employee.id,
                    module="platform",
                    organization_id=organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    after_data={"employee_code": employee.employee_code, "full_name": employee.full_name},
                    metadata={"action": "employee.create"},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action="employee.create",
                    entity_type="employee",
                    entity_id=employee.id,
                    module="platform",
                    organization_id=organization_id,
                    message=f"Employee assigned — {employee.full_name}",
                    icon="employee",
                    commit=False,
                )
                uow.record_event(
                    EmployeeCreated(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        employee_id=employee.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        return employee

    def update_employee(
        self,
        employee_id: str,
        *,
        employee_code: str | None = None,
        full_name: str | None = None,
        department_id: str | None = None,
        department: str | None = None,
        site_id: str | None = None,
        site_name: str | None = None,
        title: str | None = None,
        employment_type: EmploymentType | str | None = None,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool | None = None,
        user_id: str | None = None,
        expected_version: int | None = None,
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="update employee")
        organization_id = self._active_organization_id(operation_label="update employee")
        tenant_id = self._tenant_context_service.require_active_tenant_id(
            operation_label="update employee"
        )
        with self._uow_factory.create(context=self._new_context()) as uow:
            employee = uow.employees.get_for_organization(employee_id, organization_id)
            if employee is None:
                raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
            if expected_version is not None and employee.version != expected_version:
                raise ConcurrencyError(
                    "Employee changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            resolved_department_id = employee.department_id
            resolved_department_name = employee.department
            if department_id is not None or department is not None:
                resolved_department_id, resolved_department_name = resolve_employee_department_reference(
                    department_repo=uow.departments,
                    organization_repo=self._organization_repo,
                    active_organization_id=organization_id,
                    department_id=department_id if department_id is not None else None,
                    department_name=department if department is not None else employee.department,
                )

            resolved_site_id = employee.site_id
            resolved_site_name = employee.site_name
            if site_id is not None or site_name is not None:
                resolved_site_id, resolved_site_name = resolve_employee_site_reference(
                    site_repo=uow.sites,
                    organization_repo=self._organization_repo,
                    active_organization_id=organization_id,
                    site_id=site_id if site_id is not None else None,
                    site_name=site_name if site_name is not None else employee.site_name,
                )

            candidate = replace(
                employee,
                employee_code=employee_code if employee_code is not None else employee.employee_code,
                full_name=full_name if full_name is not None else employee.full_name,
                department_id=resolved_department_id,
                department=resolved_department_name,
                site_id=resolved_site_id,
                site_name=resolved_site_name,
                title=title if title is not None else employee.title,
                employment_type=employment_type if employment_type is not None else employee.employment_type,
                email=email if email is not None else employee.email,
                phone=phone if phone is not None else employee.phone,
                is_active=bool(is_active) if is_active is not None else employee.is_active,
                user_id=user_id if user_id is not None else employee.user_id,
            )
            other_fields_changed = (
                candidate.employee_code != employee.employee_code
                or candidate.full_name != employee.full_name
                or candidate.department_id != employee.department_id
                or candidate.department != employee.department
                or candidate.site_id != employee.site_id
                or candidate.site_name != employee.site_name
                or candidate.title != employee.title
                or candidate.employment_type != employee.employment_type
                or candidate.email != employee.email
                or candidate.phone != employee.phone
                or candidate.user_id != employee.user_id
            )
            active_state_changed = candidate.is_active != employee.is_active
            profile_changed = other_fields_changed or active_state_changed
            if not profile_changed:
                return employee
            if employee_code is not None:
                existing = uow.employees.get_by_code_for_organization(
                    candidate.employee_code,
                    organization_id,
                )
                if existing is not None and existing.id != employee.id:
                    raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")

            try:
                uow.employees.update(candidate)
                touched_resources = sync_linked_employee_resources(candidate, uow.resources)
                # A pure active-state transition (no other field changed) gets its
                # own distinct action so the curated Organization Activity feed can
                # tell "removed" (deactivated) apart from an ordinary profile edit.
                if active_state_changed and not other_fields_changed:
                    audit_action = "employee.activate" if candidate.is_active else "employee.deactivate"
                else:
                    audit_action = "employee.update"
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="employee",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization_id,
                    category="MASTER_DATA",
                    severity="low",
                    metadata={"action": audit_action},
                    commit=False,
                    fail_closed=True,
                )
                record_activity(
                    uow,
                    action=audit_action,
                    entity_type="employee",
                    entity_id=candidate.id,
                    module="platform",
                    organization_id=organization_id,
                    message=(
                        f"Employee removed — {candidate.full_name}"
                        if audit_action == "employee.deactivate"
                        else f"Employee reinstated — {candidate.full_name}"
                        if audit_action == "employee.activate"
                        else f"Employee updated — {candidate.full_name}"
                    ),
                    icon="employee",
                    type="warning" if audit_action == "employee.deactivate" else "info",
                    commit=False,
                )
                uow.record_event(
                    EmployeeProfileUpdated(
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        employee_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                if self._resource_master_event_factory is not None:
                    for resource in touched_resources:
                        uow.record_event(
                            self._resource_master_event_factory(
                                resource, tenant_id=tenant_id, organization_id=organization_id
                            )
                        )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        return candidate

    def list_employees(
        self,
        *,
        active_only: bool | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> list[Employee]:
        require_permission(self._user_session, "employee.read", operation_label="list employees")
        organization_id = self._active_organization_id(operation_label="list employees")
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
        self._active_organization_id() (the existing, unchanged domain
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
        organization_id = self._active_organization_id(
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
        organization_id = self._active_organization_id(
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
        organization_id = self._active_organization_id(
            operation_label="view employee site breakdown"
        )
        return self._headcount_reader.get_site_breakdown(
            tenant_id=tenant_id, organization_id=organization_id
        )

    def get_employee(self, employee_id: str) -> Employee:
        require_permission(self._user_session, "employee.read", operation_label="view employee")
        organization_id = self._active_organization_id(operation_label="view employee")
        employee = self._employee_repo.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        return employee

    def _active_organization_id(self, *, operation_label: str) -> str:
        if self._tenant_context_service is None:
            raise ValidationError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_organization_id(
            operation_label=operation_label,
        )


__all__ = ["EMPLOYEE_PAGE_SIZE_OPTIONS", "EmployeePage", "EmployeeService"]
