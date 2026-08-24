from __future__ import annotations

from typing import Any
from decimal import Decimal

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceCreateCommand,
    ResourceLifecycleCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.domain.enums import CostType, ResourceKind, WorkerType

from .validation import (
    optional_decimal,
    optional_float,
    require_int,
    optional_text,
    require_text,
)

def suggest_code(
    desktop_api: ProjectManagementResourcesDesktopApi,
    payload: dict[str, Any],
) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {
        str(getattr(row, "code", "") or "").upper()
        for row in desktop_api.list_resources()
    }
    name = optional_text(payload, "name")
    return CodeGenerator().generate(
        "resource",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )

def create_resource(
    desktop_api: ProjectManagementResourcesDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = ResourceCreateCommand(
        name=optional_text(payload, "name") or "",
        code=optional_text(payload, "resourceCode"),
        kind=optional_text(payload, "kind") or ResourceKind.PERSON.value,
        role=optional_text(payload, "role") or "",
        hourly_rate=optional_decimal(payload, "hourlyRate", "Hourly rate must be a valid number.", default=Decimal("0")),
        cost_type=optional_text(payload, "costType") or CostType.LABOR.value,
        currency_code=optional_text(payload, "currency"),
        capacity_percent=optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
        address=optional_text(payload, "address") or "",
        contact=optional_text(payload, "contact") or "",
        worker_type=optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
        employee_id=optional_text(payload, "employeeId"),
        department_id=optional_text(payload, "departmentId"),
        site_id=optional_text(payload, "siteId"),
    )
    desktop_api.create_resource(command)

def update_resource(
    desktop_api: ProjectManagementResourcesDesktopApi,
    payload: dict[str, Any],
) -> None:
    command = ResourceUpdateCommand(
        resource_id=require_text(payload, "resourceId", "Resource ID is required for updates."),
        name=optional_text(payload, "name") or "",
        code=optional_text(payload, "resourceCode"),
        kind=require_text(payload, "kind", "Resource kind is required."),
        role=optional_text(payload, "role") or "",
        hourly_rate=optional_decimal(payload, "hourlyRate", "Hourly rate must be a valid number.", default=Decimal("0")),
        cost_type=optional_text(payload, "costType") or CostType.LABOR.value,
        currency_code=optional_text(payload, "currency"),
        capacity_percent=optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
        address=optional_text(payload, "address") or "",
        contact=optional_text(payload, "contact") or "",
        worker_type=optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
        employee_id=optional_text(payload, "employeeId"),
        department_id=optional_text(payload, "departmentId"),
        site_id=optional_text(payload, "siteId"),
        expected_version=require_int(payload, "expectedVersion", "Resource version is required."),
    )
    desktop_api.update_resource(command)

def deactivate_resource(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    expected_version: int,
) -> None:
    normalized_resource_id = (resource_id or "").strip()
    if not normalized_resource_id:
        raise ValueError("Resource ID is required to deactivate a resource.")
    desktop_api.deactivate_resource(
        ResourceLifecycleCommand(
            resource_id=normalized_resource_id,
            expected_version=expected_version,
        )
    )

def reactivate_resource(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    expected_version: int,
) -> None:
    normalized_resource_id = (resource_id or "").strip()
    if not normalized_resource_id:
        raise ValueError("Resource ID is required to reactivate a resource.")
    desktop_api.reactivate_resource(
        ResourceLifecycleCommand(
            resource_id=normalized_resource_id,
            expected_version=expected_version,
        )
    )
