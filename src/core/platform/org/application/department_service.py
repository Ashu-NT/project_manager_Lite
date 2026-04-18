from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.audit.helpers import record_audit
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import domain_events
from src.core.platform.auth.authorization import require_any_permission, require_permission
from src.core.platform.org.contracts import (
    DepartmentRepository,
    EmployeeRepository,
    LocationReferenceRepository,
    OrganizationRepository,
    SiteRepository,
)
from src.core.platform.org.domain import Department, Organization
from src.core.platform.org.support import normalize_code, normalize_name


def _normalize_optional_text(value: str | None) -> str:
    return (value or "").strip()


def _resolve_name(*, name: str | None, display_name: str | None, label: str) -> str:
    return normalize_name(display_name if display_name is not None else name, label=label)


class DepartmentService:
    def __init__(
        self,
        session: Session,
        department_repo: DepartmentRepository,
        *,
        organization_repo: OrganizationRepository,
        site_repo: SiteRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        location_reference_repo: LocationReferenceRepository | None = None,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._department_repo = department_repo
        self._organization_repo = organization_repo
        self._site_repo = site_repo
        self._employee_repo = employee_repo
        self._location_reference_repo = location_reference_repo
        self._user_session = user_session
        self._audit_service = audit_service

    def register_location_reference_repository(
        self,
        location_reference_repo: LocationReferenceRepository | None,
    ) -> None:
        self._location_reference_repo = location_reference_repo

    def list_departments(self, *, active_only: bool | None = None) -> list[Department]:
        self._require_department_read_access("list departments")
        organization = self._active_organization()
        return self._department_repo.list_for_organization(organization.id, active_only=active_only)

    def search_departments(
        self,
        *,
        search_text: str = "",
        active_only: bool | None = True,
    ) -> list[Department]:
        self._require_department_read_access("search departments")
        normalized_search = _normalize_optional_text(search_text).lower()
        rows = self._department_repo.list_for_organization(self._active_organization().id, active_only=active_only)
        if not normalized_search:
            return rows
        return [
            department
            for department in rows
            if normalized_search in " ".join(
                filter(
                    None,
                    [
                        department.department_code,
                        department.name,
                        department.department_type,
                        department.cost_center_code,
                        department.notes,
                    ],
                )
            ).lower()
        ]

    def get_department(self, department_id: str) -> Department:
        self._require_department_read_access("view department")
        organization = self._active_organization()
        department = self._department_repo.get(department_id)
        if department is None or department.organization_id != organization.id:
            raise NotFoundError("Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND")
        return department

    def find_department_by_code(self, department_code: str) -> Department | None:
        self._require_department_read_access("resolve department")
        normalized_code = normalize_code(department_code, label="Department code")
        return self._department_repo.get_by_code(self._active_organization().id, normalized_code)

    def get_context_organization(self) -> Organization:
        require_permission(self._user_session, "settings.manage", operation_label="view department context")
        return self._active_organization()

    def list_available_location_references(
        self,
        *,
        site_id: str | None = None,
        active_only: bool | None = True,
    ) -> list[object]:
        require_permission(
            self._user_session,
            "settings.manage",
            operation_label="list department location references",
        )
        organization = self._active_organization()
        if site_id is not None:
            self._validate_site_id(site_id, organization_id=organization.id)
        if self._location_reference_repo is None:
            return []
        return list(
            self._location_reference_repo.list_for_organization(
                organization.id,
                active_only=active_only,
                site_id=site_id,
            )
        )

    def create_department(
        self,
        *,
        department_code: str,
        name: str | None = None,
        display_name: str | None = None,
        description: str = "",
        site_id: str | None = None,
        default_location_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str = "",
        cost_center_code: str = "",
        manager_employee_id: str | None = None,
        is_active: bool = True,
        notes: str = "",
    ) -> Department:
        require_permission(self._user_session, "settings.manage", operation_label="create department")
        organization = self._active_organization()
        normalized_code = normalize_code(department_code, label="Department code")
        normalized_name = _resolve_name(name=name, display_name=display_name, label="Department name")
        if self._department_repo.get_by_code(organization.id, normalized_code) is not None:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            )
        normalized_site_id = self._validate_site_id(site_id, organization_id=organization.id)
        normalized_default_location_id = self._validate_default_location_id(
            default_location_id,
            organization_id=organization.id,
            site_id=normalized_site_id,
        )
        normalized_parent_id = self._validate_parent_department_id(
            parent_department_id,
            organization_id=organization.id,
        )
        normalized_manager_id = self._validate_manager_employee_id(manager_employee_id)
        department = Department.create(
            organization_id=organization.id,
            department_code=normalized_code,
            name=normalized_name,
            description=_normalize_optional_text(description),
            site_id=normalized_site_id,
            default_location_id=normalized_default_location_id,
            parent_department_id=normalized_parent_id,
            department_type=_normalize_optional_text(department_type),
            cost_center_code=_normalize_optional_text(cost_center_code).upper(),
            manager_employee_id=normalized_manager_id,
            is_active=bool(is_active),
            notes=_normalize_optional_text(notes),
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
                "name": department.name,
                "site_id": department.site_id or "",
                "default_location_id": department.default_location_id or "",
                "department_type": department.department_type,
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
        name: str | None = None,
        display_name: str | None = None,
        description: str | None = None,
        site_id: str | None = None,
        default_location_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str | None = None,
        cost_center_code: str | None = None,
        manager_employee_id: str | None = None,
        is_active: bool | None = None,
        notes: str | None = None,
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
        if name is not None or display_name is not None:
            department.name = _resolve_name(name=name, display_name=display_name, label="Department name")
        if description is not None:
            department.description = _normalize_optional_text(description)
        target_site_id = department.site_id
        if site_id is not None:
            target_site_id = self._validate_site_id(site_id, organization_id=organization.id)
            department.site_id = target_site_id
        if default_location_id is not None:
            department.default_location_id = self._validate_default_location_id(
                default_location_id,
                organization_id=organization.id,
                site_id=target_site_id,
            )
        else:
            department.default_location_id = self._validate_default_location_id(
                department.default_location_id,
                organization_id=organization.id,
                site_id=target_site_id,
            )
        if parent_department_id is not None:
            department.parent_department_id = self._validate_parent_department_id(
                parent_department_id,
                organization_id=organization.id,
                current_department_id=department.id,
            )
        if department_type is not None:
            department.department_type = _normalize_optional_text(department_type)
        if cost_center_code is not None:
            department.cost_center_code = _normalize_optional_text(cost_center_code).upper()
        if manager_employee_id is not None:
            department.manager_employee_id = self._validate_manager_employee_id(manager_employee_id)
        if is_active is not None:
            department.is_active = bool(is_active)
        if notes is not None:
            department.notes = _normalize_optional_text(notes)
        department.updated_at = datetime.now(timezone.utc)
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
                "name": department.name,
                "site_id": department.site_id or "",
                "default_location_id": department.default_location_id or "",
                "department_type": department.department_type,
                "is_active": str(department.is_active),
            },
        )
        domain_events.departments_changed.emit(department.id)
        return department

    def _validate_site_id(self, site_id: str | None, *, organization_id: str) -> str | None:
        normalized = _normalize_optional_text(site_id) or None
        if normalized is None or self._site_repo is None:
            return normalized
        site = self._site_repo.get(normalized)
        if site is None or site.organization_id != organization_id:
            raise ValidationError("Department site must belong to the active organization.", code="DEPARTMENT_SITE_INVALID")
        return normalized

    def _validate_parent_department_id(
        self,
        parent_department_id: str | None,
        *,
        organization_id: str,
        current_department_id: str | None = None,
    ) -> str | None:
        normalized = _normalize_optional_text(parent_department_id) or None
        if normalized is None:
            return None
        if current_department_id and normalized == current_department_id:
            raise ValidationError("Department cannot be its own parent.", code="DEPARTMENT_PARENT_INVALID")
        parent = self._department_repo.get(normalized)
        if parent is None or parent.organization_id != organization_id:
            raise ValidationError(
                "Parent department must belong to the active organization.",
                code="DEPARTMENT_PARENT_INVALID",
            )
        return normalized

    def _validate_manager_employee_id(self, manager_employee_id: str | None) -> str | None:
        normalized = _normalize_optional_text(manager_employee_id) or None
        if normalized is None or self._employee_repo is None:
            return normalized
        if self._employee_repo.get(normalized) is None:
            raise ValidationError(
                "Department manager employee does not exist.",
                code="DEPARTMENT_MANAGER_INVALID",
            )
        return normalized

    def _validate_default_location_id(
        self,
        default_location_id: str | None,
        *,
        organization_id: str,
        site_id: str | None,
    ) -> str | None:
        normalized = _normalize_optional_text(default_location_id) or None
        if normalized is None:
            return None
        if self._location_reference_repo is None:
            raise ValidationError(
                "Maintenance location references are not available in the current runtime.",
                code="DEPARTMENT_LOCATION_REFERENCE_UNAVAILABLE",
            )
        location = self._location_reference_repo.get(normalized)
        if location is None or location.organization_id != organization_id:
            raise ValidationError(
                "Department default location must belong to the active organization.",
                code="DEPARTMENT_LOCATION_INVALID",
            )
        if site_id is not None and location.site_id != site_id:
            raise ValidationError(
                "Department default location must belong to the selected site.",
                code="DEPARTMENT_LOCATION_SITE_INVALID",
            )
        return normalized

    def _active_organization(self) -> Organization:
        organization = self._organization_repo.get_active()
        if organization is None:
            raise NotFoundError("Active organization not found.", code="ORGANIZATION_NOT_FOUND")
        return organization

    def _require_department_read_access(self, operation_label: str) -> None:
        require_any_permission(
            self._user_session,
            ("settings.manage", "department.read"),
            operation_label=operation_label,
        )


__all__ = ["DepartmentService"]
