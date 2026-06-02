from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SchedulingMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class SchedulingOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[SchedulingMetricViewModel, ...]


@dataclass(frozen=True)
class SchedulingSelectorOptionViewModel:
    value: str
    label: str
    supporting_text: str = ""


@dataclass(frozen=True)
class SchedulingDayOptionViewModel:
    index: int
    label: str
    checked: bool


@dataclass(frozen=True)
class SchedulingRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = False
    can_secondary_action: bool = False
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchedulingCollectionViewModel:
    title: str
    subtitle: str
    items: tuple[SchedulingRecordViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


@dataclass(frozen=True)
class SchedulingDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class SchedulingDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[SchedulingDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchedulingCalendarViewModel:
    summary_text: str
    working_day_options: tuple[SchedulingDayOptionViewModel, ...] = field(
        default_factory=tuple
    )
    hours_per_day: str = "8"
    holidays: tuple[SchedulingRecordViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


@dataclass(frozen=True)
class SchedulingBaselineCompareViewModel:
    options: tuple[SchedulingSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_baseline_a_id: str = ""
    selected_baseline_b_id: str = ""
    include_unchanged: bool = False
    summary_text: str = ""
    rows: tuple[SchedulingRecordViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


@dataclass(frozen=True)
class SchedulingWorkspaceViewModel:
    overview: SchedulingOverviewViewModel
    project_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    calendar_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    baseline_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    dependency_type_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    dependency_task_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    status_options: tuple[SchedulingSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_project_id: str = ""
    selected_calendar_id: str = "default"
    selected_baseline_id: str = ""
    selected_status_filter: str = "all"
    search_text: str = ""
    show_critical_only: bool = False
    show_delayed_only: bool = False
    page: int = 1
    page_size: int = 25
    total_count: int = 0
    selected_activity_id: str = ""
    calendar: SchedulingCalendarViewModel = field(
        default_factory=lambda: SchedulingCalendarViewModel(summary_text="")
    )
    baselines: SchedulingBaselineCompareViewModel = field(
        default_factory=SchedulingBaselineCompareViewModel
    )
    schedule: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Activity Table",
            subtitle="",
        )
    )
    timeline: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Timeline",
            subtitle="",
        )
    )
    critical_path: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Critical Path",
            subtitle="",
        )
    )
    diagnostics: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Diagnostics",
            subtitle="",
        )
    )
    delayed_activities: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Delayed Activities",
            subtitle="",
        )
    )
    resource_loading: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Resource Loading",
            subtitle="",
        )
    )
    baseline_register: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Baselines",
            subtitle="",
        )
    )
    dependencies: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Dependencies",
            subtitle="",
        )
    )
    constraints: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Constraints",
            subtitle="",
        )
    )
    constraint_violations: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Constraint Violations",
            subtitle="",
        )
    )
    activity_feed: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Planning Activity",
            subtitle="",
        )
    )
    selected_activity_detail: SchedulingDetailViewModel = field(
        default_factory=SchedulingDetailViewModel
    )


__all__ = [
    "SchedulingBaselineCompareViewModel",
    "SchedulingCalendarViewModel",
    "SchedulingCollectionViewModel",
    "SchedulingDayOptionViewModel",
    "SchedulingDetailFieldViewModel",
    "SchedulingDetailViewModel",
    "SchedulingMetricViewModel",
    "SchedulingOverviewViewModel",
    "SchedulingRecordViewModel",
    "SchedulingSelectorOptionViewModel",
    "SchedulingWorkspaceViewModel",
]
