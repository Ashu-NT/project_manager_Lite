from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.contract.uow.employee_unit_of_work import EmployeeUnitOfWorkFactory
from src.core.platform.contract.repositories.master_data.department.contracts import DepartmentRepository
from src.core.platform.application.master_data.employee.employee_support import (
    build_employee_audit_details,
    resolve_employee_department_reference,
    resolve_employee_site_reference,
    sync_linked_employee_resources,
)
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
    LinkedEmployeeResourceRepository,
)
from src.core.platform.contract.read.master_data.employee.employee_headcount_reader import (
    EmployeeDepartmentBreakdownRow,
    EmployeeHeadcountReader,
    EmployeeHeadcountSummary,
    EmployeeSiteBreakdownRow,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.domain.master_data.employee import Employee, EmploymentType
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events

if TYPE_CHECKING:
    from src.core.platform.application.history.audit.enterprise_audit_service import EnterpriseAuditService
    from src.core.platform.domain.security.auth.session import UserSessionContext


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
        uow_factory: EmployeeUnitOfWorkFactory,
    ):
        self._session = session
        self._employee_repo = employee_repo
        self._resource_repo = resource_repo
        self._site_repo = site_repo
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._headcount_reader = headcount_reader
        self._uow_factory = uow_factory
        self._tenant_context_service = tenant_context_service or (
            TenantContextService(
                organization_repo=organization_repo,
                user_session=user_session,
            )
            if organization_repo is not None
            else None
        )
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
                    severity="low",
                    metadata={"action": "employee.create", **build_employee_audit_details(employee)},
                    commit=False,
                    fail_closed=True,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        domain_events.employees_changed.emit(employee.id)
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
            if employee_code is not None:
                existing = uow.employees.get_by_code_for_organization(
                    candidate.employee_code,
                    organization_id,
                )
                if existing is not None and existing.id != employee.id:
                    raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")

            try:
                uow.employees.update(candidate)
                touched_resource_ids = sync_linked_employee_resources(candidate, uow.resources)
                record_audit_entry(
                    uow,
                    operation="update",
                    entity_type="employee",
                    entity_id=candidate.id,
                    module="platform",
                    severity="low",
                    metadata={"action": "employee.update", **build_employee_audit_details(candidate)},
                    commit=False,
                    fail_closed=True,
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        # Only emit resources_changed once the linked-resource mutations above
        # are actually durable — emitting inside sync_linked_employee_resources
        # (before commit) would fire events for rows that could still roll back.
        for resource_id in touched_resource_ids:
            domain_events.resources_changed.emit(resource_id)
        domain_events.employees_changed.emit(candidate.id)
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


__all__ = ["EmployeeService"]
