from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaintenanceReliabilityOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class MaintenanceFailureSymptomOptionViewModel:
    value: str
    label: str
    failure_code: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class MaintenanceReliabilityMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class MaintenanceReliabilityOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[MaintenanceReliabilityMetricViewModel, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class MaintenanceReliabilitySuggestionRowViewModel:
    match_scope_label: str
    root_cause_name: str
    occurrence_count: int
    total_downtime_minutes: int
    latest_occurrence_at_label: str


@dataclass(frozen=True)
class MaintenanceReliabilityInsightRowViewModel:
    failure_name: str
    root_cause_name: str
    work_order_count: int
    total_downtime_minutes: int
    open_work_orders: int


@dataclass(frozen=True)
class MaintenanceReliabilityRecurringRowViewModel:
    anchor_label: str
    failure_name: str
    leading_root_cause_name: str
    occurrence_count: int
    open_work_orders: int
    mean_interval_hours_label: str


@dataclass(frozen=True)
class MaintenanceReliabilityWorkspaceViewModel:
    overview: MaintenanceReliabilityOverviewViewModel
    site_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_site_filter: str = "all"
    asset_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_asset_filter: str = "all"
    system_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_system_filter: str = "all"
    location_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_location_filter: str = "all"
    failure_symptom_options: tuple[MaintenanceFailureSymptomOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_failure_code_filter: str = "all"
    days_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_days_filter: str = "90"
    limit_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_limit_filter: str = "20"
    threshold_options: tuple[MaintenanceReliabilityOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_threshold_filter: str = "2"
    suggestion_rows: tuple[MaintenanceReliabilitySuggestionRowViewModel, ...] = field(
        default_factory=tuple
    )
    root_cause_rows: tuple[MaintenanceReliabilityInsightRowViewModel, ...] = field(
        default_factory=tuple
    )
    recurring_rows: tuple[MaintenanceReliabilityRecurringRowViewModel, ...] = field(
        default_factory=tuple
    )
    empty_state: str = ""


__all__ = [
    "MaintenanceFailureSymptomOptionViewModel",
    "MaintenanceReliabilityInsightRowViewModel",
    "MaintenanceReliabilityMetricViewModel",
    "MaintenanceReliabilityOptionViewModel",
    "MaintenanceReliabilityOverviewViewModel",
    "MaintenanceReliabilityRecurringRowViewModel",
    "MaintenanceReliabilitySuggestionRowViewModel",
    "MaintenanceReliabilityWorkspaceViewModel",
]
