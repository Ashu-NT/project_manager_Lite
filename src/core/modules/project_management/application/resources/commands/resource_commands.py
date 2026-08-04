# src/core/modules/project_management/application/resources/commands/resource_commands.py
from __future__ import annotations

import logging
from dataclasses import replace

from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.task import AssignmentRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.platform.common.interfaces import TimeEntryRepository
from src.core.platform.contract.master_data.employee.contracts import EmployeeRepository
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.auth.authorization import require_permission
from src.core.shared.activity import record_activity
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)

logger = logging.getLogger(__name__)

def _employee_contact(employee) -> str:
    return (getattr(employee, "email", None) or getattr(employee, "phone", None) or "").strip()


class ResourceCommandMixin:
    def _resolve_resource_code(self, code: str, name: str, *, exclude_id: str | None = None) -> str:
        """Normalize a manual code or auto-generate a unique one (global scope)."""
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        existing = {
            str(getattr(resource, "code", "") or "").upper()
            for resource in self._resource_repo.list()
            if exclude_id is None or resource.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Resource code",
            )
            return manual
        return CodeGenerator().generate(
            "resource",
            exists=lambda candidate: candidate.upper() in existing,
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _resolved_worker_type(value: WorkerType | str | None) -> WorkerType:
        return Resource.create(name="Worker Type Probe", worker_type=value).worker_type

    @staticmethod
    def _is_resource_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_resources_code" in message or "resources.resource_code" in message

    @staticmethod
    def _raise_resource_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Resource code '{code}' already exists.",
            code="CODE_DUPLICATE",
        ) from exc

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
        code: str = "",
    ) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="create resource")
        organization_id = self._active_organization_id(operation_label="create resource")
        resolved_worker_type = self._resolved_worker_type(worker_type)
        resolved_name = name
        resolved_role = role
        resolved_contact = contact
        resolved_employee_id = employee_id
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
            resolved_name = employee.full_name
            resolved_role = employee.title or resolved_role
            resolved_contact = _employee_contact(employee) or resolved_contact
            resolved_employee_id = employee.id
        else:
            resolved_employee_id = None
        resource = Resource.create(
            name=resolved_name,
            code="",
            role=resolved_role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=resolve_pm_currency(
                tenant_context_service=getattr(self, "_tenant_context_service", None),
                operation_label="create resource",
                explicit=currency_code,
            ),
            capacity_percent=capacity_percent,
            address=address,
            contact=resolved_contact,
            worker_type=resolved_worker_type,
            employee_id=resolved_employee_id,
            organization_id=organization_id,
        )
        resource.code = self._resolve_resource_code(code, resource.name)
        try:
            self._resource_repo.add(resource)
            self._session.commit()
            record_activity(
                self,
                action="resource.create",
                entity_type="resource",
                entity_id=resource.id,
                module="project_management",
                details={
                    "name": resource.name,
                    "role": resource.role,
                    "capacity_percent": resource.capacity_percent,
                    "worker_type": resource.worker_type.value,
                    "employee_id": resource.employee_id or "",
                },
            )
            logger.info(f"Created resource {resource.id} - {resource.name}")
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_resource_code_integrity_error(exc):
                self._raise_resource_code_duplicate(resource.code, exc)
            logger.error(f"Error creating resource: {exc}")
            raise
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
        code: str | None = None,
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

        resolved_worker_type = (
            self._resolved_worker_type(worker_type)
            if worker_type is not None
            else getattr(resource, "worker_type", WorkerType.EXTERNAL)
        )
        resolved_employee_id = (
            employee_id
            if worker_type is not None or employee_id is not None
            else getattr(resource, "employee_id", None)
        )
        candidate = replace(
            resource,
            name=resource.name if name is None else name,
            role=resource.role if role is None else role,
            hourly_rate=resource.hourly_rate if hourly_rate is None else hourly_rate,
            is_active=resource.is_active if is_active is None else is_active,
            cost_type=resource.cost_type if cost_type is None else cost_type,
            currency_code=(
                resource.currency_code
                if currency_code is None
                else resolve_pm_currency(
                    tenant_context_service=getattr(self, "_tenant_context_service", None),
                    operation_label="update resource currency",
                    explicit=currency_code,
                )
            ),
            capacity_percent=resource.capacity_percent if capacity_percent is None else capacity_percent,
            address=resource.address if address is None else address,
            contact=resource.contact if contact is None else contact,
            worker_type=resolved_worker_type,
            employee_id=resolved_employee_id,
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
            candidate = replace(
                candidate,
                name=employee.full_name,
                role=employee.title or candidate.role,
                contact=_employee_contact(employee) or candidate.contact,
                employee_id=employee.id,
            )
        else:
            candidate = replace(candidate, employee_id=None)
        if code is not None and code.strip():
            candidate = replace(
                candidate,
                code=self._resolve_resource_code(code, candidate.name, exclude_id=resource.id),
            )

        try:
            self._resource_repo.update(candidate)
            self._session.commit()
            record_activity(
                self,
                action="resource.update",
                entity_type="resource",
                entity_id=candidate.id,
                module="project_management",
                details={
                    "name": candidate.name,
                    "role": candidate.role,
                    "capacity_percent": candidate.capacity_percent,
                    "worker_type": candidate.worker_type.value,
                    "employee_id": candidate.employee_id or "",
                },
            )
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_resource_code_integrity_error(exc):
                self._raise_resource_code_duplicate(candidate.code, exc)
            raise
        except Exception as e:
            self._session.rollback()
            raise e
        domain_events.resources_changed.emit(candidate.id)
        return candidate

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
            record_activity(
                self,
                action="resource.delete",
                entity_type="resource",
                entity_id=resource.id,
                module="project_management",
                details={"name": resource.name},
            )
        except Exception as e:
            self._session.rollback()
            raise e
        domain_events.resources_changed.emit(resource_id)


__all__ = ["ResourceCommandMixin"]
