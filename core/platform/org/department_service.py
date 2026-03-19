from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.platform.audit.helpers import record_audit
from core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.common.interfaces import DepartmentRepository, OrganizationRepository
from core.platform.common.models import Department, Organization
from core.platform.notifications.domain_events import domain_events
from core.platform.org.support import normalize_code, normalize_name


class DepartmentService:
    def __init__(
        self,
        session: Session,
        department_repo: DepartmentRepository,
        *,
        organization_repo: OrganizationRepository,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def list_departments(self, *, active_only: bool | None = None) -> list[Department]:
        require_permission(self._user_session, "settings.manage", operation_label="list departments")
        organization = self._active_organization()
        return self._department_repo.list_for_organization(organization.id, active_only=active_only)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view department context")
        return self._active_organization()

    def create_department(
        self,
        *,
        department_code: str,
        display_name: str,
        is_active: bool = True,
    ) -> Department:
        require_permission(self._user_session, "settings.manage", operation_label="create department")
        organization = self._active_organization()
        normalized_code = normalize_code(department_code, label="Department code")
        normalized_name = normalize_name(display_name, label="Department name")
        if self._department_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            )
        department = Department.create(
            organization_id=organization.id,
            department_code=normalized_code,
            display_name=normalized_name,
            is_active=bool(is_active),
        )
        try:
            self._department_repo.add(department)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="department.create",
            entity_type="department",
            entity_id=department.id,
            details={
                "organization_id": organization.id,
                "department_code": department.department_code,
                "display_name": department.display_name,
                "is_active": str(department.is_active),
            },
        )
        domain_events.departments_changed.emit(department.id)
        return department

    def update_department(
        self,
        department_id: str,
        *,
        department_code: str | None = None,
        display_name: str | None = None,
        is_active: bool | None = None,
        expected_version: int | None = None,
    ) -> Department:
        require_permission(self._user_session, "settings.manage", operation_label="update department")
        organization = self._active_organization()
        department = self._department_repo.get(department_id)
        if department is None or department.organization_id != organization.id:
            raise NotFoundError("Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND")
        if expected_version is not None and department.version != expected_version:
            raise ConcurrencyError(
                "Department changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if department_code is not None:
            normalized_code = normalize_code(department_code, label="Department code")
            existing = self._department_repo.get_by_code(organization.id, normalized_code)
            if existing is not None and existing.id != department.id:
                raise ValidationError(
                    "Department code already exists in the active organization.",
                    code="DEPARTMENT_CODE_EXISTS",
                )
            department.department_code = normalized_code
        if display_name is not None:
            department.display_name = normalize_name(display_name, label="Department name")
        if is_active is not None:
            department.is_active = bool(is_active)
        try:
            self._department_repo.update(department)
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            ) from exc
        except Exception:
            self._session.rollback()
            raise
        record_audit(
            self,
            action="department.update",
            entity_type="department",
            entity_id=department.id,
            details={
                "organization_id": organization.id,
                "department_code": department.department_code,
                "display_name": department.display_name,
                "is_active": str(department.is_active),
            },
        )
        domain_events.departments_changed.emit(department.id)
        return department

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization


__all__ = ["DepartmentService"]
