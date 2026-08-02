from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.department.domain import Department
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_events import domain_events

from .department_context import active_organization
from .department_location_service import validate_default_location_id
from .department_utils import resolve_name
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
    department = Department.create(
        organization_id=organization.id,
        department_code=department_code,
        name=resolve_name(name=name, display_name=display_name),
        description=description,
        site_id=site_id,
        default_location_id=default_location_id,
        parent_department_id=parent_department_id,
        department_type=department_type,
        cost_center_code=cost_center_code,
        manager_employee_id=manager_employee_id,
        is_active=bool(is_active),
        notes=notes,
    )
    if service._department_repo.get_by_code(organization.id, department.department_code) is not None:
        raise ValidationError(
            "Department code already exists in the active organization.",
            code="DEPARTMENT_CODE_EXISTS",
        )
    department.site_id = validate_site_id(service, department.site_id, organization_id=organization.id)
    department.default_location_id = validate_default_location_id(
        service,
        department.default_location_id,
        organization_id=organization.id,
        site_id=department.site_id,
    )
    department.parent_department_id = validate_parent_department_id(
        service,
        department.parent_department_id,
        organization_id=organization.id,
    )
    department.manager_employee_id = validate_manager_employee_id(
        service,
        department.manager_employee_id,
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
    record_audit_entry(
        service,
        operation="create",
        entity_type="department",
        entity_id=department.id,
        module="platform",
        severity="low",
        metadata={
            "action": "department.create",
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

    target_site_id = department.site_id
    if site_id is not None:
        target_site_id = validate_site_id(service, site_id, organization_id=organization.id)

    if default_location_id is not None:
        target_default_location_id = validate_default_location_id(
            service,
            default_location_id,
            organization_id=organization.id,
            site_id=target_site_id,
        )
    else:
        target_default_location_id = validate_default_location_id(
            service,
            department.default_location_id,
            organization_id=organization.id,
            site_id=target_site_id,
        )

    target_parent_department_id = department.parent_department_id
    if parent_department_id is not None:
        target_parent_department_id = validate_parent_department_id(
            service,
            parent_department_id,
            organization_id=organization.id,
            current_department_id=department.id,
        )

    target_manager_employee_id = department.manager_employee_id
    if manager_employee_id is not None:
        target_manager_employee_id = validate_manager_employee_id(service, manager_employee_id)

    candidate = replace(
        department,
        department_code=department_code if department_code is not None else department.department_code,
        name=(
            resolve_name(name=name, display_name=display_name)
            if name is not None or display_name is not None
            else department.name
        ),
        description=description if description is not None else department.description,
        site_id=target_site_id,
        default_location_id=target_default_location_id,
        parent_department_id=target_parent_department_id,
        department_type=department_type if department_type is not None else department.department_type,
        cost_center_code=cost_center_code if cost_center_code is not None else department.cost_center_code,
        manager_employee_id=target_manager_employee_id,
        is_active=bool(is_active) if is_active is not None else department.is_active,
        notes=notes if notes is not None else department.notes,
        updated_at=datetime.now(timezone.utc),
    )
    if department_code is not None:
        existing = service._department_repo.get_by_code(organization.id, candidate.department_code)
        if existing is not None and existing.id != department.id:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            )

    try:
        service._department_repo.update(candidate)
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
    record_audit_entry(
        service,
        operation="update",
        entity_type="department",
        entity_id=candidate.id,
        module="platform",
        severity="low",
        metadata={
            "action": "department.update",
            "organization_id": organization.id,
            "department_code": candidate.department_code,
            "name": candidate.name,
            "site_id": candidate.site_id or "",
            "default_location_id": candidate.default_location_id or "",
            "department_type": candidate.department_type,
            "is_active": str(candidate.is_active),
        },
    )
    domain_events.departments_changed.emit(candidate.id)
    return candidate


__all__ = ["create_department", "update_department"]
