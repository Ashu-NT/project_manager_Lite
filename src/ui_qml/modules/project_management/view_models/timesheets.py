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
    queue_status_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    queue_resource_options: tuple[TimesheetSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_queue_status: str = "SUBMITTED"
    queue_search_text: str = ""
    selected_queue_project_id: str = "all"
    selected_queue_resource_id: str = "all"
    queue_period_start_from: str = ""
    queue_period_start_to: str = ""
    queue_sort_key: str = "submittedAt"
    queue_sort_direction: str = "desc"
    selected_queue_period_id: str = ""
    review_queue: TimesheetCollectionViewModel = field(default_factory=lambda: TimesheetCollectionViewModel("", "", ""))
    review_detail: TimesheetDetailViewModel = field(default_factory=TimesheetDetailViewModel)
    empty_state: str = ""
    queue_total_count: int = 0
    queue_page: int = 1
    queue_page_size: int = 25

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
