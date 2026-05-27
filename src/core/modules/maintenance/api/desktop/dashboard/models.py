from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
)


@dataclass(frozen=True)
class MaintenanceDashboardWindowOptionDescriptor:
    value: int
    label: str


@dataclass(frozen=True)
class MaintenanceDashboardMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceDashboardOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceDashboardMetricDescriptor, ...]


@dataclass(frozen=True)
class MaintenanceDashboardBacklogRowDescriptor:
    group: str
    label: str
    value: str


@dataclass(frozen=True)
class MaintenanceDashboardRootCauseRowDescriptor:
    failure_name: str
    root_cause_name: str
    work_order_count: int
    total_downtime_minutes: int
    latest_occurrence_at_label: str
    open_work_orders: int


@dataclass(frozen=True)
class MaintenanceDashboardRecurringRowDescriptor:
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    total_downtime_minutes: int
    mean_interval_hours_label: str


@dataclass(frozen=True)
class MaintenanceDashboardSnapshotDescriptor:
    overview: MaintenanceDashboardOverviewDescriptor
    site_options: tuple[MaintenanceSiteOptionDescriptor, ...] = field(default_factory=tuple)
    selected_site_id: str = ""
    asset_options: tuple[MaintenanceAssetOptionDescriptor, ...] = field(default_factory=tuple)
    selected_asset_id: str = ""
    system_options: tuple[MaintenanceSystemOptionDescriptor, ...] = field(default_factory=tuple)
    selected_system_id: str = ""
    location_options: tuple[MaintenanceLocationOptionDescriptor, ...] = field(default_factory=tuple)
    selected_location_id: str = ""
    window_options: tuple[MaintenanceDashboardWindowOptionDescriptor, ...] = field(default_factory=tuple)
    selected_days: int = 90
    backlog_rows: tuple[MaintenanceDashboardBacklogRowDescriptor, ...] = field(default_factory=tuple)
    root_cause_rows: tuple[MaintenanceDashboardRootCauseRowDescriptor, ...] = field(default_factory=tuple)
    recurring_rows: tuple[MaintenanceDashboardRecurringRowDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "MaintenanceDashboardBacklogRowDescriptor",
    "MaintenanceDashboardMetricDescriptor",
    "MaintenanceDashboardOverviewDescriptor",
    "MaintenanceDashboardRecurringRowDescriptor",
    "MaintenanceDashboardRootCauseRowDescriptor",
    "MaintenanceDashboardSnapshotDescriptor",
    "MaintenanceDashboardWindowOptionDescriptor",
]
