from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy.exc import IntegrityError

from src.core.platform.application.master_data.department.department_context import (
    active_organization,
)
from src.core.platform.application.master_data.department.department_utils import (
    require_name,
)
from src.core.platform.application.master_data.department.department_validation import (
    validate_head_of_department_employee_id,
    validate_parent_department_id,
    validate_site_id,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.contract.use_cases.master_data.department.commands import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
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

if TYPE_CHECKING:
    from src.core.platform.domain.master_data.org import Organization



def _event_tenant_id(organization: Organization) -> str:
    # Active-context organizations are tenant-scoped; the value is passed to
    # the domain events unchanged.
    return cast(str, organization.tenant_id)


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
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.uow.master_data.department_unit_of_work import (
    DepartmentUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


def _new_context(*, causation_id: str | None = None) -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


class DepartmentCommandHandler:
    """Department lifecycle writes in the active organization: create, update,
    activate and deactivate, each in one Department UoW with audit and activity."""

    def __init__(
        self,
        *,
        uow_factory: DepartmentUnitOfWorkFactory,
        clock: Clock,
        user_session: UserSessionContext | None,
        tenant_context_service: TenantContextService | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service

    def create_department(self, command: DepartmentCreateCommand) -> Department:
        """Lifecycle is never settable through Create -- every new department
        starts ACTIVE. Use activate_department/deactivate_department afterward
        for any non-active initial state a test or import needs."""
        require_permission(self._user_session, "settings.manage", operation_label="create department")
        organization = active_organization(self._tenant_context_service)
        department = Department.create(
            organization_id=organization.id,
            department_code=command.department_code,
            name=require_name(command.name),
            description=command.description,
            site_id=command.site_id,
            parent_department_id=command.parent_department_id,
            department_type=command.department_type,
            cost_center_code=command.cost_center_code,
            head_of_department_employee_id=command.head_of_department_employee_id,
            is_active=True,
            notes=command.notes,
        )
        with self._uow_factory.create(context=_new_context()) as uow:
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
                current_department_id=department.id,
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
                        tenant_id=_event_tenant_id(organization),
                        organization_id=organization.id,
                        department_id=department.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Department code already exists in the active organization.",
                    code="DEPARTMENT_CODE_EXISTS",
                ) from exc
        return department

    def update_department(self, command: DepartmentUpdateCommand) -> Department:
        """Pure profile update -- lifecycle is never settable here; use
        activate_department/deactivate_department instead."""
        require_permission(self._user_session, "settings.manage", operation_label="update department")
        organization = active_organization(self._tenant_context_service)
        with self._uow_factory.create(context=_new_context()) as uow:
            department = uow.departments.get(command.department_id)
            if department is None or department.organization_id != organization.id:
                raise NotFoundError(
                    "Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND"
                )
            if command.expected_version is not None and department.version != command.expected_version:
                raise ConcurrencyError(
                    "Department changed since you opened it. Refresh and try again.",
                    code="STALE_WRITE",
                )

            target_site_id = department.site_id
            if command.site_id is not None:
                target_site_id = validate_site_id(uow.sites, command.site_id, organization_id=organization.id)

            target_parent_department_id = department.parent_department_id
            if command.parent_department_id is not None:
                target_parent_department_id = validate_parent_department_id(
                    uow.departments,
                    command.parent_department_id,
                    organization_id=organization.id,
                    current_department_id=department.id,
                )

            target_head_of_department_employee_id = department.head_of_department_employee_id
            if command.head_of_department_employee_id is not None:
                target_head_of_department_employee_id = validate_head_of_department_employee_id(
                    uow.employees,
                    command.head_of_department_employee_id,
                    organization_id=organization.id,
                    current_department_id=department.id,
                )

            candidate = replace(
                department,
                department_code=command.department_code if command.department_code is not None else department.department_code,
                name=command.name if command.name is not None else department.name,
                description=command.description if command.description is not None else department.description,
                site_id=target_site_id,
                parent_department_id=target_parent_department_id,
                department_type=command.department_type if command.department_type is not None else department.department_type,
                cost_center_code=command.cost_center_code if command.cost_center_code is not None else department.cost_center_code,
                head_of_department_employee_id=target_head_of_department_employee_id,
                notes=command.notes if command.notes is not None else department.notes,
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
            candidate = replace(candidate, updated_at=datetime.now(UTC))
            if command.department_code is not None:
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
                        tenant_id=_event_tenant_id(organization),
                        organization_id=organization.id,
                        department_id=candidate.id,
                        occurred_at=self._clock.now(),
                    )
                )
                uow.commit()
            except IntegrityError as exc:
                raise ValidationError(
                    "Department code already exists in the active organization.",
                    code="DEPARTMENT_CODE_EXISTS",
                ) from exc
        return candidate

    def _transition_department_status(
        self, department_id: str, *, new_is_active: bool, action: str
    ) -> Department:
        require_permission(self._user_session, "settings.manage", operation_label="change department status")
        organization = active_organization(self._tenant_context_service)
        with self._uow_factory.create(context=_new_context()) as uow:
            department = uow.departments.get(department_id)
            if department is None or department.organization_id != organization.id:
                raise NotFoundError(
                    "Department not found in the active organization.", code="DEPARTMENT_NOT_FOUND"
                )
            _require_valid_department_transition(department, new_is_active)
            candidate = replace(
                department,
                is_active=new_is_active,
                updated_at=datetime.now(UTC),
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
                    tenant_id=_event_tenant_id(organization),
                    organization_id=organization.id,
                    department_id=candidate.id,
                    occurred_at=self._clock.now(),
                )
            )
            uow.commit()
        return candidate

    def activate_department(self, department_id: str) -> Department:
        return self._transition_department_status(
            department_id, new_is_active=True, action="department.activate"
        )

    def deactivate_department(self, department_id: str) -> Department:
        return self._transition_department_status(
            department_id, new_is_active=False, action="department.deactivate"
        )


__all__ = ["DepartmentCommandHandler"]
