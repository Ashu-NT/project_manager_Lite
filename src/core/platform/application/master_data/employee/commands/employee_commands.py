from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.employee.dto.commands.employee import (
    EmployeeCreateCommand,
    EmployeeUpdateCommand,
)
from src.core.platform.application.master_data.employee.employee_context import (
    active_organization_id,
    require_tenant_context_service,
)
from src.core.platform.application.master_data.employee.employee_support import (
    resolve_employee_department_reference,
    resolve_employee_site_for_department,
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
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.security.auth.auth_repository import (
    UserRepository,
)
from src.core.platform.contract.repositories.tenant.tenancy.contracts import (
    UserTenantMembershipRepository,
)
from src.core.platform.contract.uow.master_data.employee_unit_of_work import (
    EmployeeUnitOfWorkFactory,
)
from src.core.platform.domain.master_data.employee import (
    Employee,
    EmployeeLifecycleStatus,
    EmploymentType,
)
from src.core.platform.domain.master_data.employee.events import (
    EmployeeActivated,
    EmployeeCreated,
    EmployeeDeactivated,
    EmployeeProfileUpdated,
)
from src.core.platform.domain.security.auth.user import ACCOUNT_TYPE_HUMAN
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock

if TYPE_CHECKING:
    from src.core.platform.domain.security.auth.session import UserSessionContext


EMPLOYEE_PAGE_SIZE_OPTIONS: tuple[int, ...] = (25, 50, 100)

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


class EmployeeCommandHandler:
    """Employee master-data writes in the active organization: create, update,
    lifecycle and the link to a Platform user account."""

    def __init__(
        self,
        *,
        uow_factory: EmployeeUnitOfWorkFactory,
        clock: Clock,
        organization_repo: OrganizationRepository | None,
        user_repo: UserRepository | None,
        user_tenant_repo: UserTenantMembershipRepository | None,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._organization_repo = organization_repo
        self._user_repo = user_repo
        self._user_tenant_repo = user_tenant_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_employee(self, command: EmployeeCreateCommand) -> Employee:
        # No `is_active`/`status` parameter -- every new Employee starts
        # ACTIVE (see EmployeeLifecycleStatus). Use activate_employee/
        # deactivate_employee afterward to change it. No `user_id` parameter
        # either -- System Access is a relationship operation
        # (link_employee_user_account), never ordinary profile Create.
        require_permission(self._user_session, "employee.manage", operation_label="create employee")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="create employee")
        tenant_id = require_tenant_context_service(self._tenant_context_service).require_active_tenant_id(
            operation_label="create employee"
        )
        with self._uow_factory.create(context=_new_context()) as uow:
            normalized_employee_code = (command.employee_code or "").strip().upper()
            if uow.employees.get_by_code_for_organization(normalized_employee_code, organization_id) is not None:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")
            # Resolved before constructing the domain object -- department_id
            # is a required field on Employee, so the id must already be
            # known (whether the caller passed an id directly or a name to
            # match) before Employee.create() can validate it.
            resolved_department_id, resolved_department_name = resolve_employee_department_reference(
                department_repo=uow.departments,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                department_id=command.department_id,
                department_name=command.department,
            )
            if resolved_department_id is None:
                raise ValidationError(
                    "Employee must be assigned to a department.", code="EMPLOYEE_DEPARTMENT_REQUIRED"
                )
            resolved_department = uow.departments.get(resolved_department_id)
            if resolved_department is None or resolved_department.organization_id != organization_id:
                # Structurally unreachable through the public API today --
                # resolve_employee_department_reference() already rejects a
                # department outside the active organization -- kept as an
                # explicit, defense-in-depth assertion of the invariant
                # rather than a silently-trusted implication.
                raise ValidationError(
                    "Employee department must belong to the same organization as the employee.",
                    code="EMPLOYEE_DEPARTMENT_ORGANIZATION_MISMATCH",
                )
            resolved_site_id, resolved_site_name = resolve_employee_site_for_department(
                department=resolved_department,
                site_repo=uow.sites,
                organization_repo=self._organization_repo,
                active_organization_id=organization_id,
                site_id=command.site_id,
                site_name=command.site_name,
            )
            employee = Employee.create(
                employee_code=command.employee_code,
                full_name=command.full_name,
                organization_id=organization_id,
                department_id=resolved_department_id,
                department=resolved_department_name,
                site_id=resolved_site_id,
                site_name=resolved_site_name,
                title=command.title,
                employment_type=command.employment_type,
                email=command.email,
                phone=command.phone,
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
                    message=f"Employee assigned - {employee.full_name}",
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

    def update_employee(self, command: EmployeeUpdateCommand) -> Employee:
        # No `is_active`/`status` parameter -- lifecycle is command-only
        # (activate_employee/deactivate_employee in employee_commands.py).
        # No `user_id` parameter either -- see link_employee_user_account/
        # unlink_employee_user_account.
        require_permission(self._user_session, "employee.manage", operation_label="update employee")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="update employee")
        tenant_id = require_tenant_context_service(self._tenant_context_service).require_active_tenant_id(
            operation_label="update employee"
        )
        with self._uow_factory.create(context=_new_context()) as uow:
            employee = uow.employees.get_for_organization(command.employee_id, organization_id)
            if employee is None:
                raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
            if command.expected_version is not None and employee.version != command.expected_version:
                raise ConcurrencyError(
                    "Employee changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            department_changing = command.department_id is not None or command.department is not None
            resolved_department_id = employee.department_id
            resolved_department_name = employee.department
            if department_changing:
                resolved_department_id, resolved_department_name = resolve_employee_department_reference(
                    department_repo=uow.departments,
                    organization_repo=self._organization_repo,
                    active_organization_id=organization_id,
                    department_id=command.department_id if command.department_id is not None else None,
                    department_name=command.department if command.department is not None else employee.department,
                )
                if resolved_department_id is None:
                    raise ValidationError(
                        "Employee must be assigned to a department.", code="EMPLOYEE_DEPARTMENT_REQUIRED"
                    )
                if resolved_department_id != employee.department_id:
                    current_hod_department = uow.departments.find_by_head_of_department_employee_id(employee.id)
                    if current_hod_department is not None:
                        raise ValidationError(
                            f"{employee.full_name} is the Head of Department for "
                            f"{current_hod_department.name} and cannot be moved to another department "
                            "until that department's Head of Department is cleared or reassigned.",
                            code="EMPLOYEE_TRANSFER_BLOCKED_BY_HOD_ASSIGNMENT",
                        )

            department_transferred = resolved_department_id != employee.department_id
            site_touched = command.site_id is not None or command.site_name is not None
            resolved_site_id = employee.site_id
            resolved_site_name = employee.site_name
            if department_transferred or site_touched:
                # Employee.department_id is required at runtime (field validator).
                resolved_department = uow.departments.get(cast(str, resolved_department_id))
                if resolved_department is None or resolved_department.organization_id != organization_id:
                    raise ValidationError(
                        "Employee department must belong to the same organization as the employee.",
                        code="EMPLOYEE_DEPARTMENT_ORGANIZATION_MISMATCH",
                    )
                resolved_site_id, resolved_site_name = resolve_employee_site_for_department(
                    department=resolved_department,
                    site_repo=uow.sites,
                    organization_repo=self._organization_repo,
                    active_organization_id=organization_id,
                    # Only pass through an explicit override when the caller
                    # actually touched site this call -- a bare department
                    # transfer must never be misread as "an empty site was
                    # explicitly requested" (see resolve_employee_site_for_
                    # department's own current_site_id/name preservation for
                    # an organization-wide department).
                    site_id=command.site_id if site_touched else None,
                    site_name=(command.site_name or "") if site_touched else "",
                    current_site_id=employee.site_id,
                    current_site_name=employee.site_name,
                )

            candidate = replace(
                employee,
                employee_code=command.employee_code if command.employee_code is not None else employee.employee_code,
                full_name=command.full_name if command.full_name is not None else employee.full_name,
                department_id=resolved_department_id,
                department=resolved_department_name,
                site_id=resolved_site_id,
                site_name=resolved_site_name,
                title=command.title if command.title is not None else employee.title,
                # Raw input is coerced by the field's "before" validator.
                employment_type=cast(
                    EmploymentType,
                    command.employment_type if command.employment_type is not None else employee.employment_type,
                ),
                email=command.email if command.email is not None else employee.email,
                phone=command.phone if command.phone is not None else employee.phone,
            )
            profile_changed = (
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
            )
            if not profile_changed:
                return employee
            if command.employee_code is not None:
                existing = uow.employees.get_by_code_for_organization(
                    candidate.employee_code,
                    organization_id,
                )
                if existing is not None and existing.id != employee.id:
                    raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS")

            try:
                uow.employees.update(candidate)
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
                    message=f"Employee updated - {candidate.full_name}",
                    icon="employee",
                    type="info",
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
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError("Employee code already exists.", code="EMPLOYEE_CODE_EXISTS") from exc
        return candidate

    def _transition_employee_status(
        self, employee_id: str, *, new_status: EmployeeLifecycleStatus, action: str
    ) -> Employee:
        require_permission(self._user_session, "employee.manage", operation_label="change employee status")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="change employee status")
        tenant_id = require_tenant_context_service(self._tenant_context_service).require_active_tenant_id(
            operation_label="change employee status"
        )
        with self._uow_factory.create(context=_new_context()) as uow:
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
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        return candidate

    def activate_employee(self, employee_id: str) -> Employee:
        return self._transition_employee_status(
            employee_id, new_status=EmployeeLifecycleStatus.ACTIVE, action="employee.activate"
        )

    def deactivate_employee(self, employee_id: str) -> Employee:
        return self._transition_employee_status(
            employee_id, new_status=EmployeeLifecycleStatus.INACTIVE, action="employee.deactivate"
        )

    def link_employee_user_account(self, employee_id: str, user_id: str) -> Employee:
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
        require_permission(self._user_session, "employee.manage", operation_label="link employee user account")
        require_permission(self._user_session, "auth.manage", operation_label="link employee user account")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="link employee user account")
        tenant_id = require_tenant_context_service(self._tenant_context_service).require_active_tenant_id(
            operation_label="link employee user account"
        )
        if self._user_repo is None or self._user_tenant_repo is None:
            raise RuntimeError("User repository is not configured.")
        with self._uow_factory.create(context=_new_context()) as uow:
            employee = uow.employees.get_for_organization(employee_id, organization_id)
            if employee is None:
                raise NotFoundError("Employee not found.", code="EMPLOYEE_NOT_FOUND")
            normalized_user_id = (user_id or "").strip()
            if not normalized_user_id:
                raise ValidationError("A user account is required to link.", code="EMPLOYEE_USER_LINK_REQUIRED")
            user = self._user_repo.get(normalized_user_id)
            if user is None:
                raise ValidationError("User account not found.", code="EMPLOYEE_USER_LINK_USER_NOT_FOUND")
            if self._user_tenant_repo.get(normalized_user_id, tenant_id) is None:
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

    def unlink_employee_user_account(self, employee_id: str) -> Employee:
        """The reverse of link_employee_user_account -- same permission gate,
        never touches User/RBAC state, never fires automatically from Employee
        lifecycle changes (see employee_commands.deactivate_employee, which
        deliberately leaves a linked User account untouched)."""
        require_permission(self._user_session, "employee.manage", operation_label="unlink employee user account")
        require_permission(self._user_session, "auth.manage", operation_label="unlink employee user account")
        organization_id = active_organization_id(self._tenant_context_service, operation_label="unlink employee user account")
        with self._uow_factory.create(context=_new_context()) as uow:
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



def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["EmployeeCommandHandler"]
