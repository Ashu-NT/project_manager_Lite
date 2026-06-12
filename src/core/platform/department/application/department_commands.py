from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.shared.events.domain_events import domain_events
from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.department.domain import Department
from src.core.platform.org.support import normalize_code

from .department_audit import record_department_create, record_department_update
from .department_context import active_organization
from .department_location_service import validate_default_location_id
from .department_utils import normalize_optional_text, resolve_name
from .department_validation import (
    validate_manager_employee_id,
    validate_parent_department_id,
    validate_site_id,
)

if TYPE_CHECKING:
    from .department_service import DepartmentService


def create_department(
    service: DepartmentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="create department")
    organization = active_organization(service)
    normalized_code = normalize_code(department_code, label="Department code")
    normalized_name = resolve_name(name=name, display_name=display_name, label="Department name")
    if service._department_repo.get_by_code(organization.id, normalized_code) is not None:
        raise ValidationError(
            "Department code already exists in the active organization.",
            code="DEPARTMENT_CODE_EXISTS",
        )
    normalized_site_id = validate_site_id(service, site_id, organization_id=organization.id)
    normalized_default_location_id = validate_default_location_id(
        service,
        default_location_id,
        organization_id=organization.id,
        site_id=normalized_site_id,
    )
    normalized_parent_id = validate_parent_department_id(
        service, parent_department_id, organization_id=organization.id
    )
    normalized_manager_id = validate_manager_employee_id(service, manager_employee_id)
    department = Department.create(
        organization_id=organization.id,
        department_code=normalized_code,
        name=normalized_name,
        description=normalize_optional_text(description),
        site_id=normalized_site_id,
        default_location_id=normalized_default_location_id,
        parent_department_id=normalized_parent_id,
        department_type=normalize_optional_text(department_type),
        cost_center_code=normalize_optional_text(cost_center_code).upper(),
        manager_employee_id=normalized_manager_id,
        is_active=bool(is_active),
        notes=normalize_optional_text(notes),
    )
    try:
        service._department_repo.add(department)
        service._session.commit()
    except IntegrityError as exc:
        service._session.rollback()
        raise ValidationError(
            "Department code already exists in the active organization.",
            code="DEPARTMENT_CODE_EXISTS",
        ) from exc
    except Exception:
        service._session.rollback()
        raise
    record_department_create(service, department, organization)
    domain_events.departments_changed.emit(department.id)
    return department


def update_department(
    service: DepartmentService,
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
    require_permission(service._user_session, "settings.manage", operation_label="update department")
    organization = active_organization(service)
    department = service._department_repo.get(department_id)
    if department is None or department.organization_id != organization.id:
        raise NotFoundError(
            "Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND"
        )
    if expected_version is not None and department.version != expected_version:
        raise ConcurrencyError(
            "Department changed since you opened it. Refresh and try again.",
            code="STALE_WRITE",
        )
    if department_code is not None:
        normalized_code = normalize_code(department_code, label="Department code")
        existing = service._department_repo.get_by_code(organization.id, normalized_code)
        if existing is not None and existing.id != department.id:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            )
        department.department_code = normalized_code
    if name is not None or display_name is not None:
        department.name = resolve_name(name=name, display_name=display_name, label="Department name")
    if description is not None:
        department.description = normalize_optional_text(description)
    target_site_id = department.site_id
    if site_id is not None:
        target_site_id = validate_site_id(service, site_id, organization_id=organization.id)
        department.site_id = target_site_id
    if default_location_id is not None:
        department.default_location_id = validate_default_location_id(
            service, default_location_id, organization_id=organization.id, site_id=target_site_id
        )
    else:
        department.default_location_id = validate_default_location_id(
            service, department.default_location_id, organization_id=organization.id, site_id=target_site_id
        )
    if parent_department_id is not None:
        department.parent_department_id = validate_parent_department_id(
            service,
            parent_department_id,
            organization_id=organization.id,
            current_department_id=department.id,
        )
    if department_type is not None:
        department.department_type = normalize_optional_text(department_type)
    if cost_center_code is not None:
        department.cost_center_code = normalize_optional_text(cost_center_code).upper()
    if manager_employee_id is not None:
        department.manager_employee_id = validate_manager_employee_id(service, manager_employee_id)
    if is_active is not None:
        department.is_active = bool(is_active)
    if notes is not None:
        department.notes = normalize_optional_text(notes)
    department.updated_at = datetime.now(timezone.utc)
    try:
        service._department_repo.update(department)
        service._session.commit()
    except IntegrityError as exc:
        service._session.rollback()
        raise ValidationError(
            "Department code already exists in the active organization.",
            code="DEPARTMENT_CODE_EXISTS",
        ) from exc
    except Exception:
        service._session.rollback()
        raise
    record_department_update(service, department, organization)
    domain_events.departments_changed.emit(department.id)
    return department


__all__ = ["create_department", "update_department"]
