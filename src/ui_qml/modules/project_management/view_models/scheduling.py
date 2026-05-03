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
    selected_project_id: str = ""
    calendar: SchedulingCalendarViewModel = field(
        default_factory=lambda: SchedulingCalendarViewModel(summary_text="")
    )
    baselines: SchedulingBaselineCompareViewModel = field(
        default_factory=SchedulingBaselineCompareViewModel
    )
    schedule: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Schedule Snapshot",
            subtitle="",
        )
    )
    critical_path: SchedulingCollectionViewModel = field(
        default_factory=lambda: SchedulingCollectionViewModel(
            title="Critical Path",
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
