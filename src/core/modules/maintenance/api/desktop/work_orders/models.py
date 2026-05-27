from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.maintenance.domain import (
    MaintenancePriority,
    MaintenanceWorkOrderType,
)


@dataclass(frozen=True)
class MaintenanceWorkOrderStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceWorkOrderTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceSourceWorkRequestOptionDescriptor:
    value: str
    label: str
    site_id: str
    asset_id: str | None
    component_id: str | None
    system_id: str | None
    location_id: str | None
    status: str
    status_label: str
    priority: str
    priority_label: str


@dataclass(frozen=True)
class MaintenanceWorkOrderDesktopDto:
    id: str
    site_id: str
    site_label: str
    work_order_code: str
    work_order_type: str
    work_order_type_label: str
    source_type: str
    source_type_label: str
    source_id: str | None
    source_label: str
    asset_id: str | None
    asset_label: str
    component_id: str | None
    component_label: str
    system_id: str | None
    system_label: str
    location_id: str | None
    location_label: str
    title: str
    description: str
    priority: str
    priority_label: str
    status: str
    status_label: str
    requested_by_user_id: str | None
    planner_user_id: str | None
    supervisor_user_id: str | None
    assigned_team_id: str | None
    assigned_employee_id: str | None
    assigned_employee_label: str
    planned_start: str
    planned_end: str
    actual_start: str
    actual_end: str
    requires_shutdown: bool
    permit_required: bool
    approval_required: bool
    failure_code: str
    root_cause_code: str
    downtime_minutes: int | None
    parts_cost: float | None
    labor_cost: float | None
    vendor_party_id: str | None
    vendor_party_label: str
    is_preventive: bool
    is_emergency: bool
    closed_at: str
    closed_by_user_id: str | None
    notes: str
    version: int


@dataclass(frozen=True)
class MaintenanceWorkOrderCreateCommand:
    site_id: str
    work_order_code: str = ""
    work_order_type: str = MaintenanceWorkOrderType.CORRECTIVE.value
    source_type: str = "MANUAL"
    source_id: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str = ""
    description: str = ""
    priority: str = MaintenancePriority.MEDIUM.value
    assigned_team_id: str | None = None
    requires_shutdown: bool = False
    permit_required: bool = False
    approval_required: bool = False
    vendor_party_id: str | None = None
    is_preventive: bool = False
    is_emergency: bool = False
    notes: str = ""


@dataclass(frozen=True)
class MaintenanceWorkOrderUpdateCommand:
    work_order_id: str
    work_order_code: str | None = None
    work_order_type: str | None = None
    source_id: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    system_id: str | None = None
    location_id: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    planner_user_id: str | None = None
    supervisor_user_id: str | None = None
    assigned_team_id: str | None = None
    assigned_employee_id: str | None = None
    planned_start: str | None = None
    planned_end: str | None = None
    requires_shutdown: bool | None = None
    permit_required: bool | None = None
    approval_required: bool | None = None
    failure_code: str | None = None
    root_cause_code: str | None = None
    downtime_minutes: int | None = None
    parts_cost: float | None = None
    labor_cost: float | None = None
    vendor_party_id: str | None = None
    is_preventive: bool | None = None
    is_emergency: bool | None = None
    notes: str | None = None
    expected_version: int | None = None


__all__ = [
    "MaintenanceSourceWorkRequestOptionDescriptor",
    "MaintenanceWorkOrderCreateCommand",
    "MaintenanceWorkOrderDesktopDto",
    "MaintenanceWorkOrderStatusDescriptor",
    "MaintenanceWorkOrderTypeDescriptor",
    "MaintenanceWorkOrderUpdateCommand",
]
