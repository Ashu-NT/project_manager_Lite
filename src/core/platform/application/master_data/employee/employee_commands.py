from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.master_data.employee import Employee, EmployeeLifecycleStatus
from src.core.platform.domain.master_data.employee.events import (
    EmployeeActivated,
    EmployeeDeactivated,
)
from src.core.platform.domain.security.auth.user import ACCOUNT_TYPE_HUMAN
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry

if TYPE_CHECKING:
    from src.core.platform.application.master_data.employee.employee_service import (
        EmployeeService,
    )

_EMPLOYEE_STATUS_ACTIVITY_MESSAGE: dict[str, str] = {
    "employee.activate": "Employee reinstated - {name}",
    "employee.deactivate": "Employee removed - {name}",
}
_EMPLOYEE_STATUS_EVENT_CLASS: dict[str, type] = {
    "employee.activate": EmployeeActivated,
    "employee.deactivate": EmployeeDeactivated,
}


def _require_valid_employee_transition(employee: Employee, new_status: EmployeeLifecycleStatus) -> None:
    if employee.status == new_status:
        raise ValidationError(
            f"Employee is already {new_status.value}.",
            code=f"EMPLOYEE_ALREADY_{new_status.value.upper()}",
        )


def _transition_employee_status(
    service: EmployeeService, employee_id: str, *, new_status: EmployeeLifecycleStatus, action: str
) -> Employee:
    require_permission(service._user_session, "employee.manage", operation_label="change employee status")
    organization_id = service._active_organization_id(operation_label="change employee status")
    tenant_id = service._tenant_context_service.require_active_tenant_id(
        operation_label="change employee status"
    )
    with service._uow_factory.create(context=service._new_context()) as uow:
        employee = uow.employees.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        _require_valid_employee_transition(employee, new_status)
        # Preserve the existing HOD guard: a current Head of Department
        # cannot be deactivated until that responsibility is reassigned or
        # cleared. Reassigning HOD is done through Department Edit, never
        # implicitly here.
        if new_status == EmployeeLifecycleStatus.INACTIVE:
            current_hod_department = uow.departments.find_by_head_of_department_employee_id(employee.id)
            if current_hod_department is not None:
                raise ValidationError(
                    f"{employee.full_name} is the Head of Department for "
                    f"{current_hod_department.name} and cannot be deactivated until that department's "
                    "Head of Department is cleared or reassigned.",
                    code="EMPLOYEE_DEACTIVATION_BLOCKED_BY_HOD_ASSIGNMENT",
                )
        candidate = replace(employee, status=new_status)
        uow.employees.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="employee",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization_id,
            category="MASTER_DATA",
            severity="low",
            changed_fields={"status": {"before": employee.status.value, "after": candidate.status.value}},
            metadata={"action": action},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            uow,
            action=action,
            entity_type="employee",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization_id,
            message=_EMPLOYEE_STATUS_ACTIVITY_MESSAGE[action].format(name=candidate.full_name),
            icon="employee",
            type="warning" if action == "employee.deactivate" else "info",
            commit=False,
        )
        uow.record_event(
            _EMPLOYEE_STATUS_EVENT_CLASS[action](
                tenant_id=tenant_id,
                organization_id=organization_id,
                employee_id=candidate.id,
                occurred_at=service._clock.now(),
            )
        )
        uow.commit()
    return candidate


def activate_employee(service: EmployeeService, employee_id: str) -> Employee:
    return _transition_employee_status(
        service, employee_id, new_status=EmployeeLifecycleStatus.ACTIVE, action="employee.activate"
    )


def deactivate_employee(service: EmployeeService, employee_id: str) -> Employee:
    return _transition_employee_status(
        service, employee_id, new_status=EmployeeLifecycleStatus.INACTIVE, action="employee.deactivate"
    )


def link_employee_user_account(service: EmployeeService, employee_id: str, user_id: str) -> Employee:
    """System Access is a relationship operation, not ordinary Employee
    profile editing -- gated on BOTH employee.manage (authority over this
    Employee) AND auth.manage (authority to link login identities), since
    the ability to edit basic Employee profile fields does not imply the
    authority to link arbitrary User accounts. Validates: the User exists,
    belongs to the active tenant, is not already linked to a different
    Employee, and is a human account -- never that the User is active
    (account status and the Employee relationship are separate concerns;
    a disabled User may remain linked for historical/administrative
    continuity). Never touches User/RBAC state itself."""
    require_permission(service._user_session, "employee.manage", operation_label="link employee user account")
    require_permission(service._user_session, "auth.manage", operation_label="link employee user account")
    organization_id = service._active_organization_id(operation_label="link employee user account")
    tenant_id = service._tenant_context_service.require_active_tenant_id(
        operation_label="link employee user account"
    )
    if service._user_repo is None or service._user_tenant_repo is None:
        raise RuntimeError("User repository is not configured.")
    with service._uow_factory.create(context=service._new_context()) as uow:
        employee = uow.employees.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        normalized_user_id = (user_id or "").strip()
        if not normalized_user_id:
            raise ValidationError("A user account is required to link.", code="EMPLOYEE_USER_LINK_REQUIRED")
        user = service._user_repo.get(normalized_user_id)
        if user is None:
            raise ValidationError("User account not found.", code="EMPLOYEE_USER_LINK_USER_NOT_FOUND")
        if service._user_tenant_repo.get(normalized_user_id, tenant_id) is None:
            raise ValidationError(
                "User account does not belong to the active tenant.",
                code="EMPLOYEE_USER_LINK_CROSS_TENANT",
            )
        if user.account_type != ACCOUNT_TYPE_HUMAN:
            raise ValidationError(
                "Only human user accounts can be linked to an Employee.",
                code="EMPLOYEE_USER_LINK_INVALID_ACCOUNT_TYPE",
            )
        existing_link = uow.employees.find_by_user_id(normalized_user_id)
        if existing_link is not None and existing_link.id != employee.id:
            raise ValidationError(
                f"This user account is already linked to {existing_link.full_name}.",
                code="EMPLOYEE_USER_LINK_ALREADY_LINKED",
            )
        if employee.user_id == normalized_user_id:
            return employee
        candidate = replace(employee, user_id=normalized_user_id)
        uow.employees.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="employee",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization_id,
            category="PRIVILEGED_OPERATION",
            severity="medium",
            changed_fields={"user_id": {"before": employee.user_id, "after": candidate.user_id}},
            metadata={"action": "employee.link_user_account"},
            commit=False,
            fail_closed=True,
        )
        uow.commit()
    return candidate


def unlink_employee_user_account(service: EmployeeService, employee_id: str) -> Employee:
    """The reverse of link_employee_user_account -- same permission gate,
    never touches User/RBAC state, never fires automatically from Employee
    lifecycle changes (see employee_commands.deactivate_employee, which
    deliberately leaves a linked User account untouched)."""
    require_permission(service._user_session, "employee.manage", operation_label="unlink employee user account")
    require_permission(service._user_session, "auth.manage", operation_label="unlink employee user account")
    organization_id = service._active_organization_id(operation_label="unlink employee user account")
    with service._uow_factory.create(context=service._new_context()) as uow:
        employee = uow.employees.get_for_organization(employee_id, organization_id)
        if employee is None:
            raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
        if employee.user_id is None:
            return employee
        candidate = replace(employee, user_id=None)
        uow.employees.update(candidate)
        record_audit_entry(
            uow,
            operation="update",
            entity_type="employee",
            entity_id=candidate.id,
            module="platform",
            organization_id=organization_id,
            category="PRIVILEGED_OPERATION",
            severity="medium",
            changed_fields={"user_id": {"before": employee.user_id, "after": None}},
            metadata={"action": "employee.unlink_user_account"},
            commit=False,
            fail_closed=True,
        )
        uow.commit()
    return candidate


__all__ = [
    "activate_employee",
    "deactivate_employee",
    "link_employee_user_account",
    "unlink_employee_user_account",
]
