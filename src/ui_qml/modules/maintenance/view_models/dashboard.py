from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceDashboardOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceMetricViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MaintenanceDashboardBacklogRowViewModel:
    group: str
    label: str
    value: str


@dataclass(frozen=True)
class MaintenanceDashboardRootCauseRowViewModel:
    failure_name: str
    root_cause_name: str
    work_order_count: int
    total_downtime_minutes: int
    latest_occurrence_at_label: str
    open_work_orders: int


@dataclass(frozen=True)
class MaintenanceDashboardRecurringRowViewModel:
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    total_downtime_minutes: int
    mean_interval_hours_label: str


@dataclass(frozen=True)
class MaintenanceDashboardWorkspaceViewModel:
    overview: MaintenanceDashboardOverviewViewModel
    site_options: tuple[MaintenanceOptionViewModel, ...] = field(default_factory=tuple)
    selected_site_filter: str = "all"
    asset_options: tuple[MaintenanceOptionViewModel, ...] = field(default_factory=tuple)
    selected_asset_filter: str = "all"
    system_options: tuple[MaintenanceOptionViewModel, ...] = field(default_factory=tuple)
    selected_system_filter: str = "all"
    location_options: tuple[MaintenanceOptionViewModel, ...] = field(default_factory=tuple)
    selected_location_filter: str = "all"
    window_options: tuple[MaintenanceOptionViewModel, ...] = field(default_factory=tuple)
    selected_days_filter: str = "90"
    backlog_rows: tuple[MaintenanceDashboardBacklogRowViewModel, ...] = field(
        default_factory=tuple
    )
    root_cause_rows: tuple[MaintenanceDashboardRootCauseRowViewModel, ...] = field(
        default_factory=tuple
    )
    recurring_rows: tuple[MaintenanceDashboardRecurringRowViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenanceDashboardBacklogRowViewModel",
    "MaintenanceDashboardOverviewViewModel",
    "MaintenanceDashboardRecurringRowViewModel",
    "MaintenanceDashboardRootCauseRowViewModel",
    "MaintenanceDashboardWorkspaceViewModel",
    "MaintenanceMetricViewModel",
    "MaintenanceOptionViewModel",
]
