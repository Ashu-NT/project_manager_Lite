# src/core/modules/project_management/application/resources/commands/resource_commands.py
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from src.core.modules.project_management.domain.enums import CostType, ResourceKind, WorkerType
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.shared.activity import record_activity
from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)

def _employee_contact(employee) -> str:
    return (getattr(employee, "email", None) or getattr(employee, "phone", None) or "").strip()


class ResourceCommandMixin:
    def _resolve_resource_code(self, code: str, name: str, *, exclude_id: str | None = None) -> str:
        """Normalize or generate a code unique in the active tenant/org scope."""
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: self._resource_repo.code_exists(
                    candidate,
                    exclude_id=exclude_id,
                ),
                label="Resource code",
            )
            return manual
        return CodeGenerator().generate(
            "resource",
            exists=lambda candidate: self._resource_repo.code_exists(
                candidate,
                exclude_id=exclude_id,
            ),
            name=(name or "").strip() or None,
            use_year=not bool((name or "").strip()),
        )

    @staticmethod
    def _resolved_worker_type(value: WorkerType | str | None) -> WorkerType:
        if value is None:
            return WorkerType.EXTERNAL
        if isinstance(value, WorkerType):
            return value
        try:
            return WorkerType(str(value).strip().upper())
        except ValueError as exc:
            raise ValidationError(
                "Worker type must be EMPLOYEE or EXTERNAL.",
                code="RESOURCE_WORKER_TYPE_INVALID",
            ) from exc

    def _resolve_master_scope(
        self,
        *,
        kind: ResourceKind | str,
        worker_type: WorkerType | str,
        employee_id: str | None,
        department_id: str | None,
        site_id: str | None,
        exclude_resource_id: str | None = None,
    ) -> tuple[ResourceKind, WorkerType, object | None, str | None, str | None]:
        resolved_kind = kind if isinstance(kind, ResourceKind) else ResourceKind(str(kind).upper())
        resolved_worker_type = self._resolved_worker_type(worker_type)
        organization_id = self._active_organization_id(operation_label="validate resource scope")
        employee = None

        if resolved_kind == ResourceKind.PERSON:
            if resolved_worker_type == WorkerType.EMPLOYEE and not employee_id:
                raise ValidationError(
                    "Employee resources require an employee selection.",
                    code="RESOURCE_EMPLOYEE_REQUIRED",
                )
            if employee_id:
                if self._employee_repo is None:
                    raise BusinessRuleError(
                        "The employee directory is not configured.",
                        code="EMPLOYEE_DIRECTORY_REQUIRED",
                    )
                employee = self._employee_repo.get(employee_id)
                if employee is None or getattr(employee, "organization_id", None) != organization_id:
                    raise ValidationError(
                        "Selected employee was not found in the active organization.",
                        code="EMPLOYEE_NOT_FOUND",
                    )
                if not getattr(employee, "is_active", True):
                    raise ValidationError("Selected employee is inactive.", code="EMPLOYEE_INACTIVE")
                if self._resource_repo.employee_link_exists(
                    employee.id,
                    exclude_id=exclude_resource_id,
                ):
                    raise ValidationError(
                        "The selected employee is already linked to another resource.",
                        code="RESOURCE_EMPLOYEE_DUPLICATE",
                    )
                department_id = getattr(employee, "department_id", None)
                site_id = getattr(employee, "site_id", None)
        elif employee_id:
            raise ValidationError(
                "Only person resources may link to a directory identity.",
                code="RESOURCE_EMPLOYEE_LINK_INVALID",
            )

        if department_id:
            department_service = getattr(self, "_department_service", None)
            if department_service is None:
                raise BusinessRuleError(
                    "The department directory is not configured.",
                    code="DEPARTMENT_DIRECTORY_REQUIRED",
                )
            department = department_service.get_department(department_id)
            if not getattr(department, "is_active", True):
                raise ValidationError(
                    "Selected department is inactive.",
                    code="DEPARTMENT_INACTIVE",
                )
            department_site_id = getattr(department, "site_id", None)
            if site_id and department_site_id and site_id != department_site_id:
                raise ValidationError(
                    "Selected site does not match the department site.",
                    code="RESOURCE_SITE_DEPARTMENT_MISMATCH",
                )

        if site_id:
            site_service = getattr(self, "_site_service", None)
            if site_service is None:
                raise BusinessRuleError(
                    "The site directory is not configured.",
                    code="SITE_DIRECTORY_REQUIRED",
                )
            site = site_service.get_site(site_id)
            if not getattr(site, "is_active", True):
                raise ValidationError("Selected site is inactive.", code="SITE_INACTIVE")

        return resolved_kind, resolved_worker_type, employee, department_id, site_id

    @staticmethod
    def _require_expected_version(resource: Resource, expected_version: int) -> None:
        if resource.version != expected_version:
            raise ConcurrencyError(
                "Resource changed since you opened it. Reload and try again.",
                code="STALE_WRITE",
            )

    def _stage_activity(self, resource: Resource, *, action: str) -> None:
        record_activity(
            self,
            action=action,
            entity_type="resource",
            entity_id=resource.id,
            module="project_management",
            details={
                "name": resource.name,
                "kind": resource.kind.value,
                "version": resource.version,
                "capacity_percent": resource.capacity_percent,
                "worker_type": resource.worker_type.value,
                "employee_id": resource.employee_id or "",
            },
            commit=False,
        )

    def create_resource(
        self,
        name: str,
        role: str = "",
        *,
        code: str = "",
        kind: ResourceKind | str = ResourceKind.PERSON,
        hourly_rate: Decimal | int | str = Decimal("0"),
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        is_active: bool = True,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType | str = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="create resource")
        organization_id = self._active_organization_id(operation_label="create resource")
        kind, worker_type, employee, department_id, site_id = self._resolve_master_scope(
            kind=kind,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
        )
        if employee is not None:
            name = employee.full_name
            role = employee.title or role
            contact = _employee_contact(employee) or contact
            employee_id = employee.id

        resource = Resource.create(
            name=name,
            code="",
            kind=kind,
            role=role,
            hourly_rate=hourly_rate,
            is_active=bool(is_active),
            cost_type=cost_type,
            currency_code=resolve_pm_currency(
                tenant_context_service=getattr(self, "_tenant_context_service", None),
                operation_label="create resource",
                explicit=currency_code,
            ),
            capacity_percent=capacity_percent,
            address=address,
            contact=contact,
            worker_type=worker_type,
            employee_id=employee_id,
            organization_id=organization_id,
            department_id=department_id,
            site_id=site_id,
        )
        resource.code = self._resolve_resource_code(code, resource.name)
        self._resource_repo.add(resource)
        self._stage_activity(resource, action="resource.created")
        self._session.flush()
        return resource

    def update_resource(
        self,
        *,
        resource_id: str,
        expected_version: int,
        name: str,
        code: str,
        kind: ResourceKind | str,
        role: str,
        hourly_rate: Decimal | int | str,
        cost_type: CostType,
        currency_code: str | None,
        capacity_percent: float,
        address: str,
        contact: str,
        worker_type: WorkerType | str,
        employee_id: str | None,
        department_id: str | None,
        site_id: str | None,
    ) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="update resource")
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        self._require_expected_version(resource, expected_version)
        kind, worker_type, employee, department_id, site_id = self._resolve_master_scope(
            kind=kind,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
            exclude_resource_id=resource.id,
        )
        if kind != resource.kind and self._resource_repo.reference_summary(
            resource.id
        ).has_operational_references:
            raise BusinessRuleError(
                "Resource kind cannot change after the resource is used by project work.",
                code="RESOURCE_KIND_CHANGE_REFERENCED",
            )
        if employee is not None:
            name = employee.full_name
            role = employee.title or role
            contact = _employee_contact(employee) or contact
            employee_id = employee.id

        candidate = replace(
            resource,
            name=name,
            code=self._resolve_resource_code(code, name, exclude_id=resource.id),
            kind=kind,
            role=role,
            hourly_rate=hourly_rate,
            cost_type=cost_type,
            currency_code=resolve_pm_currency(
                tenant_context_service=getattr(self, "_tenant_context_service", None),
                operation_label="update resource currency",
                explicit=currency_code,
            ),
            capacity_percent=capacity_percent,
            address=address,
            contact=contact,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
        )
        self._resource_repo.update(candidate)
        self._stage_activity(candidate, action="resource.updated")
        self._session.flush()
        return candidate

    def _change_resource_lifecycle(
        self,
        *,
        resource_id: str,
        expected_version: int,
        active: bool,
    ) -> Resource:
        operation = "reactivate" if active else "deactivate"
        require_permission(
            self._user_session,
            "resource.manage",
            operation_label=f"{operation} resource",
        )
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        self._require_expected_version(resource, expected_version)
        if resource.is_active == active:
            state = "active" if active else "inactive"
            raise BusinessRuleError(
                f"Resource is already {state}.",
                code="RESOURCE_LIFECYCLE_NO_CHANGE",
            )
        candidate = replace(resource, is_active=active)
        self._resource_repo.update(candidate)
        self._stage_activity(candidate, action=f"resource.{operation}d")
        self._session.flush()
        return candidate

    def deactivate_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        return self._change_resource_lifecycle(
            resource_id=resource_id,
            expected_version=expected_version,
            active=False,
        )

    def reactivate_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        return self._change_resource_lifecycle(
            resource_id=resource_id,
            expected_version=expected_version,
            active=True,
        )

    def purge_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        require_permission(self._user_session, "resource.manage", operation_label="purge resource")
        resource = self._resource_repo.get(resource_id)
        if resource is None:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        self._require_expected_version(resource, expected_version)
        references = self._resource_repo.reference_summary(resource.id)
        if references.has_any_references:
            raise BusinessRuleError(
                "Referenced resources cannot be purged. Deactivate this resource instead.",
                code="RESOURCE_REFERENCED_CANNOT_PURGE",
            )
        self._resource_repo.delete(resource.id)
        self._stage_activity(resource, action="resource.purged")
        self._session.flush()
        return resource


__all__ = ["ResourceCommandMixin"]
