from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TimesheetMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class TimesheetOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[TimesheetMetricViewModel, ...]


@dataclass(frozen=True)
class TimesheetSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class TimesheetRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = False
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TimesheetCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str
    items: tuple[TimesheetRecordViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TimesheetDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class TimesheetDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[TimesheetDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TimesheetsWorkspaceViewModel:
    overview: TimesheetOverviewViewModel
    project_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    assignment_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    period_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    queue_status_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_project_id: str = "all"
    selected_assignment_id: str = ""
    selected_period_start: str = ""
    selected_queue_status: str = "SUBMITTED"
    selected_entry_id: str = ""
    selected_queue_period_id: str = ""
    assignment_summary: TimesheetDetailViewModel = field(default_factory=TimesheetDetailViewModel)
    entries: TimesheetCollectionViewModel = field(default_factory=lambda: TimesheetCollectionViewModel("", "", ""))
    selected_entry_detail: TimesheetDetailViewModel = field(default_factory=TimesheetDetailViewModel)
    review_queue: TimesheetCollectionViewModel = field(default_factory=lambda: TimesheetCollectionViewModel("", "", ""))
    review_detail: TimesheetDetailViewModel = field(default_factory=TimesheetDetailViewModel)
    empty_state: str = ""


__all__ = [
    "TimesheetCollectionViewModel",
    "TimesheetDetailFieldViewModel",
    "TimesheetDetailViewModel",
    "TimesheetMetricViewModel",
    "TimesheetOverviewViewModel",
    "TimesheetRecordViewModel",
    "TimesheetSelectorOptionViewModel",
    "TimesheetsWorkspaceViewModel",
]
