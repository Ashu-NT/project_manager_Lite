from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenancePlannerOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenancePlannerMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenancePlannerOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenancePlannerMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenancePlannerRequestRowViewModel:
    id: str
    request_label: str
    anchor_label: str
    status_label: str
    priority_label: str


@dataclass(frozen=True)
class MaintenancePlannerWorkOrderRowViewModel:
    id: str
    work_order_label: str
    work_order_type_label: str
    status_label: str
    priority_label: str
    plan_window_label: str


@dataclass(frozen=True)
class MaintenancePlannerMaterialRiskRowViewModel:
    id: str
    work_order_id: str
    work_order_label: str
    material_label: str
    procurement_status_label: str
    quantity_label: str
    storeroom_label: str


@dataclass(frozen=True)
class MaintenancePlannerPreventiveRowViewModel:
    plan_id: str
    plan_label: str
    anchor_label: str
    due_state_label: str
    due_reason: str
    generation_target_label: str
    trigger_label: str
    next_due_label: str
    is_due_soon: bool


@dataclass(frozen=True)
class MaintenancePlannerRecurringRowViewModel:
    anchor_id: str
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    sensor_exception_count: int


@dataclass(frozen=True)
class MaintenancePlannerWorkspaceViewModel:
    overview: MaintenancePlannerOverviewViewModel
    site_options: tuple[MaintenancePlannerOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    asset_options: tuple[MaintenancePlannerOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_asset_filter: str = "all"
    system_options: tuple[MaintenancePlannerOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_system_filter: str = "all"
    request_queue_options: tuple[MaintenancePlannerOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_request_queue: str = ""
    work_order_queue_options: tuple[MaintenancePlannerOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_work_order_queue: str = ""
    search_text: str = ""
    request_rows: tuple[MaintenancePlannerRequestRowViewModel, ...] = field(
        default_factory=tuple
    )
    work_order_rows: tuple[MaintenancePlannerWorkOrderRowViewModel, ...] = field(
        default_factory=tuple
    )
    material_rows: tuple[MaintenancePlannerMaterialRiskRowViewModel, ...] = field(
        default_factory=tuple
    )
    preventive_rows: tuple[MaintenancePlannerPreventiveRowViewModel, ...] = field(
        default_factory=tuple
    )
    recurring_rows: tuple[MaintenancePlannerRecurringRowViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenancePlannerMaterialRiskRowViewModel",
    "MaintenancePlannerMetricViewModel",
    "MaintenancePlannerOptionViewModel",
    "MaintenancePlannerOverviewViewModel",
    "MaintenancePlannerPreventiveRowViewModel",
    "MaintenancePlannerRecurringRowViewModel",
    "MaintenancePlannerRequestRowViewModel",
    "MaintenancePlannerWorkOrderRowViewModel",
    "MaintenancePlannerWorkspaceViewModel",
]
