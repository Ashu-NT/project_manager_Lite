from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import EmployeeRepository, ResourceRepository
from core.platform.common.models import Employee, EmploymentType, WorkerType
from core.platform.notifications.domain_events import domain_events


def _normalize_email(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def _normalize_phone(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _coerce_employment_type(value: EmploymentType | str | None) -> EmploymentType:
    if isinstance(value, EmploymentType):
        return value
    raw = str(value or EmploymentType.FULL_TIME.value).strip().upper()
    try:
        return EmploymentType(raw)
    except ValueError as exc:
        raise ValidationError("Employment type is invalid.", code="EMPLOYEE_TYPE_INVALID") from exc


def _employee_contact(employee: Employee) -> str:
    return employee.email or employee.phone or ""


class EmployeeService:
    def __init__(
        self,
        session: Session,
        employee_repo: EmployeeRepository,
        *,
        resource_repo: ResourceRepository | None = None,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._employee_repo = employee_repo
        self._resource_repo = resource_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def create_employee(
        self,
        *,
        employee_code: str,
        full_name: str,
        department: str = "",
        title: str = "",
        employment_type: EmploymentType | str = EmploymentType.FULL_TIME,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="create employee")
        normalized_code = (employee_code or "").strip().upper()
        normalized_name = (full_name or "").strip()
        if not normalized_code:
            raise ValidationError("Employee code is required.", code="EMPLOYEE_CODE_REQUIRED")
        if not normalized_name:
            raise ValidationError("Employee name is required.", code="EMPLOYEE_NAME_REQUIRED")
        if self._employee_repo.get_by_code(normalized_code) is not None:
            raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")

        employee = Employee.create(
            employee_code=normalized_code,
            full_name=normalized_name,
            department=(department or "").strip(),
            title=(title or "").strip(),
            employment_type=_coerce_employment_type(employment_type),
            email=_normalize_email(email),
            phone=_normalize_phone(phone),
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
            details={
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "department": employee.department,
                "title": employee.title,
            },
        )
        domain_events.employees_changed.emit(employee.id)
        return employee

    def update_employee(
        self,
        employee_id: str,
        *,
        employee_code: str | None = None,
        full_name: str | None = None,
        department: str | None = None,
        title: str | None = None,
        employment_type: EmploymentType | str | None = None,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="update employee")
        employee = self._employee_repo.get(employee_id)
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
            existing = self._employee_repo.get_by_code(normalized_code)
            if existing is not None and existing.id != employee.id:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")
            employee.employee_code = normalized_code
        if full_name is not None:
            normalized_name = (full_name or "").strip()
            if not normalized_name:
                raise ValidationError("Employee name is required.", code="EMPLOYEE_NAME_REQUIRED")
            employee.full_name = normalized_name
        if department is not None:
            employee.department = (department or "").strip()
        if title is not None:
            employee.title = (title or "").strip()
        if employment_type is not None:
            employee.employment_type = _coerce_employment_type(employment_type)
        if email is not None:
            employee.email = _normalize_email(email)
        if phone is not None:
            employee.phone = _normalize_phone(phone)
        if is_active is not None:
            employee.is_active = bool(is_active)

        try:
            self._employee_repo.update(employee)
            self._sync_linked_resources(employee)
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
            details={
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "department": employee.department,
                "title": employee.title,
                "is_active": str(employee.is_active),
            },
        )
        domain_events.employees_changed.emit(employee.id)
        return employee

    def list_employees(self, *, active_only: bool | None = None) -> list[Employee]:
        require_permission(self._user_session, "employee.read", operation_label="list employees")
        return self._employee_repo.list_all(active_only=active_only)

    def get_employee(self, employee_id: str) -> Employee:
        require_permission(self._user_session, "employee.read", operation_label="view employee")
        employee = self._employee_repo.get(employee_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        return employee

    def _sync_linked_resources(self, employee: Employee) -> None:
        if self._resource_repo is None:
            return
        for resource in self._resource_repo.list_by_employee(employee.id):
            if getattr(resource, "worker_type", WorkerType.EXTERNAL) != WorkerType.EMPLOYEE:
                continue
            resource.name = employee.full_name
            if employee.title:
                resource.role = employee.title
            resource.contact = _employee_contact(employee)
            self._resource_repo.update(resource)
            domain_events.resources_changed.emit(resource.id)


__all__ = ["EmployeeService"]
