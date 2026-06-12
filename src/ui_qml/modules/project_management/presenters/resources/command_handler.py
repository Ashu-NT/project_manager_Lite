from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementResourcesDesktopApi,
    ResourceCreateCommand,
    ResourceUpdateCommand,
)
from src.core.modules.project_management.domain.enums import CostType, WorkerType

from .validation import (
    optional_bool,
    optional_float,
    optional_int,
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
        role=optional_text(payload, "role") or "",
        hourly_rate=optional_float(payload, "hourlyRate", "Hourly rate must be a valid number.", default=0.0),
        is_active=optional_bool(payload, "isActive", default=True),
        cost_type=optional_text(payload, "costType") or CostType.LABOR.value,
        currency_code=optional_text(payload, "currency"),
        capacity_percent=optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
        address=optional_text(payload, "address") or "",
        contact=optional_text(payload, "contact") or "",
        worker_type=optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
        employee_id=optional_text(payload, "employeeId"),
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
        role=optional_text(payload, "role") or "",
        hourly_rate=optional_float(payload, "hourlyRate", "Hourly rate must be a valid number.", default=0.0),
        is_active=optional_bool(payload, "isActive", default=True),
        cost_type=optional_text(payload, "costType") or CostType.LABOR.value,
        currency_code=optional_text(payload, "currency"),
        capacity_percent=optional_float(payload, "capacityPercent", "Capacity must be a valid number.", default=100.0),
        address=optional_text(payload, "address") or "",
        contact=optional_text(payload, "contact") or "",
        worker_type=optional_text(payload, "workerType") or WorkerType.EXTERNAL.value,
        employee_id=optional_text(payload, "employeeId"),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_resource(command)

def toggle_resource_active(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
    expected_version: int | None = None,
) -> None:
    normalized_resource_id = (resource_id or "").strip()
    if not normalized_resource_id:
        raise ValueError("Resource ID is required to update availability.")
    desktop_api.toggle_resource_active(normalized_resource_id, expected_version=expected_version)

def delete_resource(
    desktop_api: ProjectManagementResourcesDesktopApi,
    resource_id: str,
) -> None:
    normalized_resource_id = (resource_id or "").strip()
    if not normalized_resource_id:
        raise ValueError("Resource ID is required to delete a resource.")
    desktop_api.delete_resource(normalized_resource_id)
