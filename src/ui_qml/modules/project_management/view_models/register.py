from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RegisterMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class RegisterOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[RegisterMetricViewModel, ...]


@dataclass(frozen=True)
class RegisterSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class RegisterRecordViewModel:
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
class RegisterDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class RegisterDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[RegisterDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RegisterCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str
    items: tuple[RegisterRecordViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RegisterWorkspaceViewModel:
    overview: RegisterOverviewViewModel
    project_options: tuple[RegisterSelectorOptionViewModel, ...] = field(default_factory=tuple)
    type_options: tuple[RegisterSelectorOptionViewModel, ...] = field(default_factory=tuple)
    status_options: tuple[RegisterSelectorOptionViewModel, ...] = field(default_factory=tuple)
    severity_options: tuple[RegisterSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_project_id: str = "all"
    selected_type_filter: str = "all"
    selected_status_filter: str = "all"
    selected_severity_filter: str = "all"
    search_text: str = ""
    entries: RegisterCollectionViewModel = field(default_factory=lambda: RegisterCollectionViewModel("", "", ""))
    selected_entry_id: str = ""
    selected_entry_detail: RegisterDetailViewModel = field(default_factory=RegisterDetailViewModel)
    urgent_entries: RegisterCollectionViewModel = field(default_factory=lambda: RegisterCollectionViewModel("", "", ""))
    empty_state: str = ""


__all__ = [
    "RegisterCollectionViewModel",
    "RegisterDetailFieldViewModel",
    "RegisterDetailViewModel",
    "RegisterMetricViewModel",
    "RegisterOverviewViewModel",
    "RegisterRecordViewModel",
    "RegisterSelectorOptionViewModel",
    "RegisterWorkspaceViewModel",
]
