from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.audit.helpers import record_audit
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.department.contracts import DepartmentRepository
from src.core.platform.employee.application.employee_support import (
    build_employee_audit_details,
    resolve_employee_department_reference,
    resolve_employee_site_reference,
    sync_linked_employee_resources,
)
from src.core.platform.employee.contracts import (
    EmployeeRepository,
    LinkedEmployeeResourceRepository,
)
from src.core.platform.employee.domain import Employee, EmploymentType
from src.core.platform.employee.support import (
    coerce_employment_type,
    normalize_email,
    normalize_phone,
)
from src.core.platform.org.contracts import OrganizationRepository
from src.core.platform.site.contracts import SiteRepository
from src.core.platform.tenancy.tenant_context import TenantContextService

if TYPE_CHECKING:
    from src.core.platform.audit.application.audit_service import AuditService
    from src.core.platform.auth.domain.session import UserSessionContext


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
        audit_service: AuditService | None = None,
    ):
        self._session = session
        self._employee_repo = employee_repo
        self._resource_repo = resource_repo
        self._site_repo = site_repo
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._tenant_context_service = tenant_context_service or (
            TenantContextService(
                organization_repo=organization_repo,
                user_session=user_session,
            )
            if organization_repo is not None
            else None
        )
        self._user_session = user_session
        self._audit_service = audit_service

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
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="create employee")
        organization_id = self._active_organization_id(operation_label="create employee")
        normalized_code = (employee_code or "").strip().upper()
        normalized_name = (full_name or "").strip()
        if not normalized_code:
            raise ValidationError("Employee code is required.", code="EMPLOYEE_CODE_REQUIRED")
        if not normalized_name:
            raise ValidationError("Employee name is required.", code="EMPLOYEE_NAME_REQUIRED")
        if self._employee_repo.get_by_code_for_organization(normalized_code, organization_id) is not None:
            raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")
        resolved_department_id, resolved_department_name = resolve_employee_department_reference(
            department_repo=self._department_repo,
            organization_repo=self._organization_repo,
            active_organization_id=organization_id,
            department_id=department_id,
            department_name=department or "",
        )
        resolved_site_id, resolved_site_name = resolve_employee_site_reference(
            site_repo=self._site_repo,
            organization_repo=self._organization_repo,
            active_organization_id=organization_id,
            site_id=site_id,
            site_name=site_name,
        )

        employee = Employee.create(
            employee_code=normalized_code,
            full_name=normalized_name,
            department_id=resolved_department_id,
            department=resolved_department_name,
            site_id=resolved_site_id,
            site_name=resolved_site_name,
            title=(title or "").strip(),
            employment_type=coerce_employment_type(employment_type),
            email=normalize_email(email),
            phone=normalize_phone(phone),
            is_active=bool(is_active),
        )
        try:
            self._employee_repo.add(employee)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="employee.create",
            entity_type="employee",
            entity_id=employee.id,
            details=build_employee_audit_details(employee),
        )
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
        expected_version: int | None = None,
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="update employee")
        organization_id = self._active_organization_id(operation_label="update employee")
        employee = self._employee_repo.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        if expected_version is not None and employee.version != expected_version:
            raise ConcurrencyError(
                "Employee changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if employee_code is not None:
            normalized_code = (employee_code or "").strip().upper()
            if not normalized_code:
                raise ValidationError("Employee code is required.", code="EMPLOYEE_CODE_REQUIRED")
            existing = self._employee_repo.get_by_code_for_organization(
                normalized_code,
                organization_id,
            )
            if existing is not None and existing.id != employee.id:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")
            employee.employee_code = normalized_code
        if full_name is not None:
            normalized_name = (full_name or "").strip()
            if not normalized_name:
                raise ValidationError("Employee name is required.", code="EMPLOYEE_NAME_REQUIRED")
            employee.full_name = normalized_name
        if department_id is not None or department is not None:
            employee.department_id, employee.department = resolve_employee_department_reference(
                department_repo=self._department_repo,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                department_id=department_id if department_id is not None else None,
                department_name=department if department is not None else employee.department,
            )
        if site_id is not None or site_name is not None:
            employee.site_id, employee.site_name = resolve_employee_site_reference(
                site_repo=self._site_repo,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                site_id=site_id if site_id is not None else None,
                site_name=site_name if site_name is not None else employee.site_name,
            )
        if title is not None:
            employee.title = (title or "").strip()
        if employment_type is not None:
            employee.employment_type = coerce_employment_type(employment_type)
        if email is not None:
            employee.email = normalize_email(email)
        if phone is not None:
            employee.phone = normalize_phone(phone)
        if is_active is not None:
            employee.is_active = bool(is_active)

        try:
            self._employee_repo.update(employee)
            sync_linked_employee_resources(employee, self._resource_repo)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="employee.update",
            entity_type="employee",
            entity_id=employee.id,
            details=build_employee_audit_details(employee),
        )
        domain_events.employees_changed.emit(employee.id)
        return employee

    def list_employees(self, *, active_only: bool | None = None) -> list[Employee]:
        require_permission(self._user_session, "employee.read", operation_label="list employees")
        organization_id = self._active_organization_id(operation_label="list employees")
        return self._employee_repo.list_for_organization(organization_id, active_only=active_only)

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
