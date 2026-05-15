from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
)


MAINTENANCE_PLANNER_OPEN_REQUESTS = "OPEN_REQUESTS"
MAINTENANCE_PLANNER_ALL_REQUESTS = "ALL_REQUESTS"
MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS = "BACKLOG_WORK_ORDERS"
MAINTENANCE_PLANNER_ALL_WORK_ORDERS = "ALL_WORK_ORDERS"


@dataclass(frozen=True)
class MaintenancePlannerMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenancePlannerOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[MaintenancePlannerMetricDescriptor, ...]


@dataclass(frozen=True)
class MaintenancePlannerQueueDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenancePlannerRequestRowDescriptor:
    id: str
    request_label: str
    anchor_label: str
    status: str
    status_label: str
    priority: str
    priority_label: str


@dataclass(frozen=True)
class MaintenancePlannerWorkOrderRowDescriptor:
    id: str
    work_order_label: str
    work_order_type: str
    work_order_type_label: str
    status: str
    status_label: str
    priority: str
    priority_label: str
    plan_window_label: str


@dataclass(frozen=True)
class MaintenancePlannerMaterialRiskRowDescriptor:
    id: str
    work_order_id: str
    work_order_label: str
    material_label: str
    procurement_status: str
    procurement_status_label: str
    quantity_label: str
    storeroom_label: str


@dataclass(frozen=True)
class MaintenancePlannerPreventiveRowDescriptor:
    plan_id: str
    plan_code: str
    plan_name: str
    plan_label: str
    anchor_label: str
    due_state: str
    due_state_label: str
    due_reason: str
    generation_target: str
    generation_target_label: str
    trigger_label: str
    next_due_label: str
    is_due_soon: bool


@dataclass(frozen=True)
class MaintenancePlannerRecurringRowDescriptor:
    anchor_id: str
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    sensor_exception_count: int


@dataclass(frozen=True)
class MaintenancePlannerSnapshotDescriptor:
    overview: MaintenancePlannerOverviewDescriptor
    site_options: tuple[MaintenanceSiteOptionDescriptor, ...] = field(default_factory=tuple)
    selected_site_id: str = ""
    asset_options: tuple[MaintenanceAssetOptionDescriptor, ...] = field(default_factory=tuple)
    selected_asset_id: str = ""
    system_options: tuple[MaintenanceSystemOptionDescriptor, ...] = field(default_factory=tuple)
    selected_system_id: str = ""
    request_queue_options: tuple[MaintenancePlannerQueueDescriptor, ...] = field(default_factory=tuple)
    selected_request_queue: str = MAINTENANCE_PLANNER_OPEN_REQUESTS
    work_order_queue_options: tuple[MaintenancePlannerQueueDescriptor, ...] = field(default_factory=tuple)
    selected_work_order_queue: str = MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS
    search_text: str = ""
    request_rows: tuple[MaintenancePlannerRequestRowDescriptor, ...] = field(default_factory=tuple)
    work_order_rows: tuple[MaintenancePlannerWorkOrderRowDescriptor, ...] = field(default_factory=tuple)
    material_rows: tuple[MaintenancePlannerMaterialRiskRowDescriptor, ...] = field(default_factory=tuple)
    preventive_rows: tuple[MaintenancePlannerPreventiveRowDescriptor, ...] = field(default_factory=tuple)
    recurring_rows: tuple[MaintenancePlannerRecurringRowDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "MAINTENANCE_PLANNER_ALL_REQUESTS",
    "MAINTENANCE_PLANNER_ALL_WORK_ORDERS",
    "MAINTENANCE_PLANNER_BACKLOG_WORK_ORDERS",
    "MAINTENANCE_PLANNER_OPEN_REQUESTS",
    "MaintenancePlannerMaterialRiskRowDescriptor",
    "MaintenancePlannerMetricDescriptor",
    "MaintenancePlannerOverviewDescriptor",
    "MaintenancePlannerPreventiveRowDescriptor",
    "MaintenancePlannerQueueDescriptor",
    "MaintenancePlannerRecurringRowDescriptor",
    "MaintenancePlannerRequestRowDescriptor",
    "MaintenancePlannerSnapshotDescriptor",
    "MaintenancePlannerWorkOrderRowDescriptor",
]
