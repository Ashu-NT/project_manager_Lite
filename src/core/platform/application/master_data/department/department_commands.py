from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.master_data.department import Department
from src.core.platform.domain.master_data.department.events import (
    DepartmentActivated,
    DepartmentCreated,
    DepartmentDeactivated,
    DepartmentProfileUpdated,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

from .department_context import active_organization
from .department_utils import resolve_name
from .department_validation import (
    validate_head_of_department_employee_id,
    validate_parent_department_id,
    validate_site_id,
)

if TYPE_CHECKING:
    from .department_service import DepartmentService


def create_department(
    service: DepartmentService,
    *,
    department_code: str,
    name: str ,
    display_name: str | None = None,
    description: str = "",
    site_id: str | None = None,
    parent_department_id: str | None = None,
    department_type: str = "",
    cost_center_code: str = "",
    head_of_department_employee_id: str | None = None,
    notes: str = "",
) -> Department:
    """Lifecycle is never settable through Create -- every new department
    starts ACTIVE. Use activate_department/deactivate_department afterward
    for any non-active initial state a test or import needs."""
    require_permission(service._user_session, "settings.manage", operation_label="create department")
    organization = active_organization(service)
    department = Department.create(
        organization_id=organization.id,
        department_code=department_code,
        name=resolve_name(name=name, display_name=display_name),
        description=description,
        site_id=site_id,
        parent_department_id=parent_department_id,
        department_type=department_type,
        cost_center_code=cost_center_code,
        head_of_department_employee_id=head_of_department_employee_id,
        is_active=True,
        notes=notes,
    )
    with service._uow_factory.create(context=service._new_context()) as uow:
        if uow.departments.get_by_code(organization.id, department.department_code) is not None:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            )
        department.site_id = validate_site_id(uow.sites, department.site_id, organization_id=organization.id)
        department.parent_department_id = validate_parent_department_id(
            uow.departments,
            department.parent_department_id,
            organization_id=organization.id,
        )
        department.head_of_department_employee_id = validate_head_of_department_employee_id(
            uow.employees,
            department.head_of_department_employee_id,
            organization_id=organization.id,
        )
        try:
            uow.departments.add(department)
            record_audit_entry(
                uow,
                operation="create",
                entity_type="department",
                entity_id=department.id,
                module="platform",
                organization_id=organization.id,
                category="MASTER_DATA",
                severity="low",
                after_data={"department_code": department.department_code, "name": department.name},
                metadata={"action": "department.create"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="department.create",
                entity_type="department",
                entity_id=department.id,
                module="platform",
                organization_id=organization.id,
                message=f"Department created — {department.name}",
                icon="department",
                commit=False,
            )
            uow.record_event(
                DepartmentCreated(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    department_id=department.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            ) from exc
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
    parent_department_id: str | None = None,
    department_type: str | None = None,
    cost_center_code: str | None = None,
    head_of_department_employee_id: str | None = None,
    notes: str | None = None,
    expected_version: int | None = None,
) -> Department:
    """Pure profile update -- lifecycle is never settable here; use
    activate_department/deactivate_department instead."""
    require_permission(service._user_session, "settings.manage", operation_label="update department")
    organization = active_organization(service)
    with service._uow_factory.create(context=service._new_context()) as uow:
        department = uow.departments.get(department_id)
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
            target_site_id = validate_site_id(uow.sites, site_id, organization_id=organization.id)

        target_parent_department_id = department.parent_department_id
        if parent_department_id is not None:
            target_parent_department_id = validate_parent_department_id(
                uow.departments,
                parent_department_id,
                organization_id=organization.id,
                current_department_id=department.id,
            )

        target_head_of_department_employee_id = department.head_of_department_employee_id
        if head_of_department_employee_id is not None:
            target_head_of_department_employee_id = validate_head_of_department_employee_id(
                uow.employees, head_of_department_employee_id, organization_id=organization.id
            )

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
            parent_department_id=target_parent_department_id,
            department_type=department_type if department_type is not None else department.department_type,
            cost_center_code=cost_center_code if cost_center_code is not None else department.cost_center_code,
            head_of_department_employee_id=target_head_of_department_employee_id,
            notes=notes if notes is not None else department.notes,
        )
        profile_changed = (
            candidate.department_code != department.department_code
            or candidate.name != department.name
            or candidate.description != department.description
            or candidate.site_id != department.site_id
            or candidate.parent_department_id != department.parent_department_id
            or candidate.department_type != department.department_type
            or candidate.cost_center_code != department.cost_center_code
            or candidate.head_of_department_employee_id != department.head_of_department_employee_id
            or candidate.notes != department.notes
        )
        if not profile_changed:
            return department
        candidate = replace(candidate, updated_at=datetime.now(timezone.utc))
        if department_code is not None:
            existing = uow.departments.get_by_code(organization.id, candidate.department_code)
            if existing is not None and existing.id != department.id:
                raise ValidationError(
                    "Department code already exists in the active organization.",
                    code="DEPARTMENT_CODE_EXISTS",
                )

        try:
            uow.departments.update(candidate)
            record_audit_entry(
                uow,
                operation="update",
                entity_type="department",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                category="MASTER_DATA",
                severity="low",
                metadata={"action": "department.update"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                uow,
                action="department.update",
                entity_type="department",
                entity_id=candidate.id,
                module="platform",
                organization_id=organization.id,
                message=f"Department updated — {candidate.name}",
                icon="department",
                commit=False,
            )
            uow.record_event(
                DepartmentProfileUpdated(
                    tenant_id=organization.tenant_id,
                    organization_id=organization.id,
                    department_id=candidate.id,
                    occurred_at=service._clock.now(),
                )
            )
            uow.commit()
        except IntegrityError as exc:
            raise ValidationError(
                "Department code already exists in the active organization.",
                code="DEPARTMENT_CODE_EXISTS",
            ) from exc
    return candidate


_DEPARTMENT_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "department.activate": "Department activated — {name}",
    "department.deactivate": "Department deactivated — {name}",
}
_DEPARTMENT_STATUS_EVENT_CLASS: dict[str, type] = {
    "department.activate": DepartmentActivated,
    "department.deactivate": DepartmentDeactivated,
}


def _require_valid_department_transition(department: Department, new_is_active: bool) -> None:
    if department.is_active == new_is_active:
        state = "active" if new_is_active else "inactive"
        raise ValidationError(
            f"Department is already {state}.",
            code=f"DEPARTMENT_ALREADY_{state.upper()}",
        )


def _transition_department_status(
    service: DepartmentService, department_id: str, *, new_is_active: bool, action: str
) -> Department:
    require_permission(service._user_session, "settings.manage", operation_label="change department status")
    organization = active_organization(service)
    with service._uow_factory.create(context=service._new_context()) as uow:
        department = uow.departments.get(department_id)
        if department is None or department.organization_id != organization.id:
            raise NotFoundError(
                "Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND"
            )
        _require_valid_department_transition(department, new_is_active)
        candidate = replace(
            department,
            is_active=new_is_active,
            updated_at=datetime.now(timezone.utc),
        )
        uow.departments.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="department",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization.id,
            category="PRIVILEGED_OPERATION",
            severity="medium",
            changed_fields={
                "status": {
                    "before": "active" if department.is_active else "inactive",
                    "after": "active" if candidate.is_active else "inactive",
                }
            },
            after_data={"department_code": candidate.department_code, "name": candidate.name},
            metadata={"action": action},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action=action,
            entity_type="department",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization.id,
            message=_DEPARTMENT_STATUS_ACTIVITY_MESSAGE[action].format(name=candidate.name),
            icon="department",
            type="info" if action == "department.activate" else "warning",
            commit=False,
        )
        uow.record_event(
            _DEPARTMENT_STATUS_EVENT_CLASS[action](
                tenant_id=organization.tenant_id,
                organization_id=organization.id,
                department_id=candidate.id,
                occurred_at=service._clock.now(),
            )
        )
        uow.commit()
    return candidate


def activate_department(service: DepartmentService, department_id: str) -> Department:
    return _transition_department_status(
        service, department_id, new_is_active=True, action="department.activate"
    )


def deactivate_department(service: DepartmentService, department_id: str) -> Department:
    return _transition_department_status(
        service, department_id, new_is_active=False, action="department.deactivate"
    )


__all__ = ["activate_department", "create_department", "deactivate_department", "update_department"]
