from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FinancialsMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class FinancialsOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[FinancialsMetricViewModel, ...]


@dataclass(frozen=True)
class FinancialsSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class FinancialsRecordViewModel:
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
class FinancialsDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class FinancialsDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[FinancialsDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialsCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str = ""
    items: tuple[FinancialsRecordViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FinancialsWorkspaceViewModel:
    overview: FinancialsOverviewViewModel
    project_options: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    cost_type_options: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    task_options: tuple[FinancialsSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_project_id: str = ""
    selected_cost_type: str = "all"
    search_text: str = ""
    costs: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    selected_cost_id: str = ""
    selected_cost_detail: FinancialsDetailViewModel = field(default_factory=FinancialsDetailViewModel)
    cashflow: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    ledger: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    source_analytics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    cost_type_analytics: FinancialsCollectionViewModel = field(default_factory=lambda: FinancialsCollectionViewModel(title="", subtitle=""))
    notes: tuple[str, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "FinancialsCollectionViewModel",
    "FinancialsDetailFieldViewModel",
    "FinancialsDetailViewModel",
    "FinancialsMetricViewModel",
    "FinancialsOverviewViewModel",
    "FinancialsRecordViewModel",
    "FinancialsSelectorOptionViewModel",
    "FinancialsWorkspaceViewModel",
]
