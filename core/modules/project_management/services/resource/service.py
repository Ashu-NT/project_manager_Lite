# core/modules/project_management/services/resource/service.py
from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

from core.platform.common.models import CostType, Resource, WorkerType
from core.platform.common.interfaces import (
    AssignmentRepository,
    EmployeeRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TimeEntryRepository,
)
from core.platform.common.exceptions import ConcurrencyError, NotFoundError, ValidationError
from core.platform.auth.authorization import require_permission
from core.platform.audit.helpers import record_audit
from core.platform.notifications.domain_events import domain_events
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin

logger = logging.getLogger(__name__)

DEFAULT_CURRENCY_CODE = "EUR"


def _normalize_worker_type(value: WorkerType | str | None) -> WorkerType:
    if isinstance(value, WorkerType):
        return value
    raw = str(value or WorkerType.EXTERNAL.value).strip().upper()
    try:
        return WorkerType(raw)
    except ValueError as exc:
        raise ValidationError("Worker type is invalid.", code="RESOURCE_WORKER_TYPE_INVALID") from exc


def _employee_contact(employee) -> str:
    return (getattr(employee, "email", None) or getattr(employee, "phone", None) or "").strip()


def _normalize_capacity_percent(value: float | None) -> float:
    resolved = float(value if value is not None else 100.0)
    if resolved <= 0.0:
        raise ValidationError("Capacity percent must be greater than zero.")
    return resolved


class ResourceService(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        session: Session,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        project_resource_repo: ProjectResourceRepository | None = None,
        time_entry_repo: TimeEntryRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        user_session=None,
        audit_service=None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._resource_repo: ResourceRepository = resource_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._time_entry_repo: TimeEntryRepository | None = time_entry_repo
        self._employee_repo: EmployeeRepository | None = employee_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._module_catalog_service = module_catalog_service

    def create_resource(
        self,
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType | str = WorkerType.EXTERNAL,
        employee_id: str | None = None,
    ) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="create resource")
        resolved_worker_type = _normalize_worker_type(worker_type)
        employee = None
        if resolved_worker_type == WorkerType.EMPLOYEE:
            if not employee_id:
                raise ValidationError("Employee resource requires an employee selection.")
            if self._employee_repo is None:
                raise ValidationError("Employee directory is not available.")
            employee = self._employee_repo.get(employee_id)
            if employee is None:
                raise ValidationError("Selected employee was not found.", code="EMPLOYEE_NOT_FOUND")
            if not getattr(employee, "is_active", True):
                raise ValidationError("Selected employee is inactive.", code="EMPLOYEE_INACTIVE")
        else:
            employee_id = None
        resolved_name = (name or "").strip()
        resolved_role = (role or "").strip()
        resolved_contact = (contact or "").strip()
        if employee is not None:
            resolved_name = employee.full_name
            resolved_role = employee.title or resolved_role
            resolved_contact = _employee_contact(employee) or resolved_contact
        if not resolved_name:
            raise ValidationError("Resource name cannot be empty.")
        if hourly_rate < 0:
            raise ValidationError("Hourly rate cannot be negative.")
        resolved_currency = (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE
        resolved_capacity = _normalize_capacity_percent(capacity_percent)
        resource = Resource.create(
            name=resolved_name,
            role=resolved_role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=resolved_currency,
            capacity_percent=resolved_capacity,
            address=(address or "").strip(),
            contact=resolved_contact,
            worker_type=resolved_worker_type,
            employee_id=employee_id,
        )
        try:
            self._resource_repo.add(resource)
            self._session.commit()
            record_audit(
                self,
                action="resource.create",
                entity_type="resource",
                entity_id=resource.id,
                details={
                    "name": resource.name,
                    "role": resource.role,
                    "capacity_percent": resource.capacity_percent,
                    "worker_type": resource.worker_type.value,
                    "employee_id": resource.employee_id or "",
                },
            )
            logger.info(f"Created resource {resource.id} - {resource.name}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error creating resource: {e}")
            raise 
        domain_events.resources_changed.emit(resource.id)
        return resource

    def update_resource(
        self,
        resource_id: str,
        name: str | None = None,
        role: str | None = None,
        hourly_rate: float | None = None,
        is_active: bool | None = None,
        cost_type: CostType | None = None,
        currency_code: str | None = None,
        capacity_percent: float | None = None,
        address: str | None = None,
        contact: str | None = None,
        worker_type: WorkerType | str | None = None,
        employee_id: str | None = None,
        expected_version: int | None = None,
    ) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="update resource")
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        if expected_version is not None and resource.version != expected_version:
            raise ConcurrencyError(
                "Resource changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )

        if name is not None:
            if not name.strip():
                raise ValidationError("Resource name cannot be empty.")
            resource.name = name.strip()
        if role is not None:
            resource.role = role.strip()
        if hourly_rate is not None:
            if hourly_rate < 0:
                raise ValidationError("Hourly rate cannot be negative.")
            resource.hourly_rate = hourly_rate
        if is_active is not None:
            resource.is_active = is_active
        if cost_type is not None:
            resource.cost_type = cost_type
        if currency_code is not None:
            resource.currency_code = currency_code.strip().upper() or None
        if capacity_percent is not None:
            resource.capacity_percent = _normalize_capacity_percent(capacity_percent)
        if address is not None:
            resource.address = address.strip()
        if contact is not None:
            resource.contact = contact.strip()
        resolved_worker_type = (
            _normalize_worker_type(worker_type)
            if worker_type is not None
            else getattr(resource, "worker_type", WorkerType.EXTERNAL)
        )
        resolved_employee_id = (
            employee_id
            if worker_type is not None or employee_id is not None
            else getattr(resource, "employee_id", None)
        )
        if resolved_worker_type == WorkerType.EMPLOYEE:
            if not resolved_employee_id:
                raise ValidationError("Employee resource requires an employee selection.")
            if self._employee_repo is None:
                raise ValidationError("Employee directory is not available.")
            employee = self._employee_repo.get(resolved_employee_id)
            if employee is None:
                raise ValidationError("Selected employee was not found.", code="EMPLOYEE_NOT_FOUND")
            if not getattr(employee, "is_active", True):
                raise ValidationError("Selected employee is inactive.", code="EMPLOYEE_INACTIVE")
            resource.name = employee.full_name
            if employee.title:
                resource.role = employee.title
            resource.contact = _employee_contact(employee)
        else:
            resolved_employee_id = None
        resource.worker_type = resolved_worker_type
        resource.employee_id = resolved_employee_id

        try:
            self._resource_repo.update(resource)
            self._session.commit()
            record_audit(
                self,
                action="resource.update",
                entity_type="resource",
                entity_id=resource.id,
                details={
                    "name": resource.name,
                    "role": resource.role,
                    "capacity_percent": resource.capacity_percent,
                    "worker_type": resource.worker_type.value,
                    "employee_id": resource.employee_id or "",
                },
            )
            
        except Exception as e:
            self._session.rollback()
            raise e
        domain_events.resources_changed.emit(resource.id)
        return resource

    def list_resources(self) -> List[Resource]:
        require_permission(self._user_session, "resource.read", operation_label="list resources")
        return self._resource_repo.list_all()

    def get_resource(self, resource_id: str) -> Resource:
        require_permission(self._user_session, "resource.read", operation_label="view resource")
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        return resource

    def delete_resource(self, resource_id: str) -> None:
        require_permission(self._user_session, "resource.manage", operation_label="delete resource")
        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")

        try:
            # delete assignments and Project- Resource first
            assignments = self._assignment_repo.list_by_resource(resource_id)
            for a in assignments:
                if self._time_entry_repo is not None:
                    self._time_entry_repo.delete_by_assignment(a.id)
                self._assignment_repo.delete(a.id)
            if self._project_resource_repo is not None:
                self._project_resource_repo.delete_by_resource(resource_id)
                 
            self._resource_repo.delete(resource_id)
            self._session.commit()
            record_audit(
                self,
                action="resource.delete",
                entity_type="resource",
                entity_id=resource.id,
                details={"name": resource.name},
            )
        except Exception as e:
            self._session.rollback()
            raise e
        domain_events.resources_changed.emit(resource_id)


