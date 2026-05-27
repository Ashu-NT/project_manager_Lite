from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.domain import (
    MaintenancePriority,
    MaintenanceWorkRequestSourceType,
)


@dataclass(frozen=True)
class MaintenancePriorityDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkRequestSourceTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkRequestStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkRequestDesktopDto:
    id: str
    site_id: str
    site_label: str
    asset_id: str | None
    asset_label: str
    component_id: str | None
    component_label: str
    system_id: str | None
    system_label: str
    location_id: str | None
    location_label: str
    work_request_code: str
    source_type: str
    source_type_label: str
    request_type: str
    source_id: str | None
    title: str
    description: str
    priority: str
    priority_label: str
    status: str
    status_label: str
    requested_at: str
    requested_by_user_id: str | None
    requested_by_name: str
    triaged_at: str
    triaged_by_user_id: str | None
    triaged_by_label: str
    failure_symptom_code: str
    safety_risk_level: str
    production_impact_level: str
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceWorkRequestCreateCommand:
    site_id: str
    work_request_code: str = ""
    source_type: str = MaintenanceWorkRequestSourceType.MANUAL.value
    source_id: str | None = None
    source_plan_task_ids: tuple[str, ...] = ()
    request_type: str = ""
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str = ""
    description: str = ""
    priority: str = MaintenancePriority.MEDIUM.value
    failure_symptom_code: str = ""
    safety_risk_level: str = ""
    production_impact_level: str = ""
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceWorkRequestUpdateCommand:
    work_request_id: str
    work_request_code: str | None = None
    request_type: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    failure_symptom_code: str | None = None
    safety_risk_level: str | None = None
    production_impact_level: str | None = None
    notes: str | None = None
    expected_version: int | None = None


__all__ = [
    "MaintenancePriorityDescriptor",
    "MaintenanceWorkRequestCreateCommand",
    "MaintenanceWorkRequestDesktopDto",
    "MaintenanceWorkRequestSourceTypeDescriptor",
    "MaintenanceWorkRequestStatusDescriptor",
    "MaintenanceWorkRequestUpdateCommand",
]
