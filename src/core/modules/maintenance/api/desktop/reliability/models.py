from __future__ import annotations

from dataclasses import dataclass, field

from src.core.modules.maintenance.api.desktop.shared_options import (
    MaintenanceAssetOptionDescriptor,
    MaintenanceLocationOptionDescriptor,
    MaintenanceSiteOptionDescriptor,
    MaintenanceSystemOptionDescriptor,
)


@dataclass(frozen=True)
class MaintenanceReliabilityChoiceDescriptor:
    value: int
    label: str


@dataclass(frozen=True)
class MaintenanceFailureSymptomOptionDescriptor:
    value: str
    label: str
    failure_code: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class MaintenanceReliabilityMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceReliabilityOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceReliabilityMetricDescriptor, ...]


@dataclass(frozen=True)
class MaintenanceReliabilitySuggestionRowDescriptor:
    match_scope_label: str
    root_cause_name: str
    occurrence_count: int
    total_downtime_minutes: int
    latest_occurrence_at_label: str


@dataclass(frozen=True)
class MaintenanceReliabilityInsightRowDescriptor:
    failure_name: str
    root_cause_name: str
    work_order_count: int
    total_downtime_minutes: int
    open_work_orders: int


@dataclass(frozen=True)
class MaintenanceReliabilityRecurringRowDescriptor:
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    mean_interval_hours_label: str


@dataclass(frozen=True)
class MaintenanceReliabilitySnapshotDescriptor:
    overview: MaintenanceReliabilityOverviewDescriptor
    site_options: tuple[MaintenanceSiteOptionDescriptor, ...] = field(default_factory=tuple)
    selected_site_id: str = ""
    asset_options: tuple[MaintenanceAssetOptionDescriptor, ...] = field(default_factory=tuple)
    selected_asset_id: str = ""
    system_options: tuple[MaintenanceSystemOptionDescriptor, ...] = field(default_factory=tuple)
    selected_system_id: str = ""
    location_options: tuple[MaintenanceLocationOptionDescriptor, ...] = field(default_factory=tuple)
    selected_location_id: str = ""
    failure_symptom_options: tuple[MaintenanceFailureSymptomOptionDescriptor, ...] = field(default_factory=tuple)
    selected_failure_code: str = ""
    days_options: tuple[MaintenanceReliabilityChoiceDescriptor, ...] = field(default_factory=tuple)
    selected_days: int = 90
    limit_options: tuple[MaintenanceReliabilityChoiceDescriptor, ...] = field(default_factory=tuple)
    selected_limit: int = 20
    threshold_options: tuple[MaintenanceReliabilityChoiceDescriptor, ...] = field(default_factory=tuple)
    selected_threshold: int = 2
    suggestion_rows: tuple[MaintenanceReliabilitySuggestionRowDescriptor, ...] = field(default_factory=tuple)
    root_cause_rows: tuple[MaintenanceReliabilityInsightRowDescriptor, ...] = field(default_factory=tuple)
    recurring_rows: tuple[MaintenanceReliabilityRecurringRowDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "MaintenanceFailureSymptomOptionDescriptor",
    "MaintenanceReliabilityChoiceDescriptor",
    "MaintenanceReliabilityInsightRowDescriptor",
    "MaintenanceReliabilityMetricDescriptor",
    "MaintenanceReliabilityOverviewDescriptor",
    "MaintenanceReliabilityRecurringRowDescriptor",
    "MaintenanceReliabilitySnapshotDescriptor",
    "MaintenanceReliabilitySuggestionRowDescriptor",
]
