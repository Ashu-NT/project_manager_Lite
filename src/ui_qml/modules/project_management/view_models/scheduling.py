from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.modules.project_management.api.desktop.scheduling.models import (
    GanttProjectionDto,
)

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
class SchedulingCalendarViewModel:
    summary_text: str
    working_day_options: tuple[SchedulingDayOptionViewModel, ...] = field(
        default_factory=tuple
    )
    hours_per_day: str = "8"
    holidays: tuple[SchedulingRecordViewModel, ...] = field(default_factory=tuple)
    calendar_id: str = ""
    calendar_name: str = ""
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
    sort_key: str = "schedule"
    sort_direction: str = "asc"
    selected_activity_id: str = ""
    gantt_projection: GanttProjectionDto | None = None
    calendar: SchedulingCalendarViewModel = field(
        default_factory=lambda: SchedulingCalendarViewModel(summary_text="")
    )
    baselines: SchedulingBaselineCompareViewModel = field(
        default_factory=SchedulingBaselineCompareViewModel
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
__all__ = [
    "SchedulingBaselineCompareViewModel",
    "SchedulingCalendarViewModel",
    "SchedulingCollectionViewModel",
    "SchedulingDayOptionViewModel",
    "SchedulingMetricViewModel",
    "SchedulingOverviewViewModel",
    "SchedulingRecordViewModel",
    "SchedulingSelectorOptionViewModel",
    "SchedulingWorkspaceViewModel",
]
