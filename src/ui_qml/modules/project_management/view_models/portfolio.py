from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PortfolioMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class PortfolioOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[PortfolioMetricViewModel, ...]


@dataclass(frozen=True)
class PortfolioSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class PortfolioRecordViewModel:
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
class PortfolioCollectionViewModel:
    title: str
    subtitle: str
    empty_state: str
    items: tuple[PortfolioRecordViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PortfolioSummaryFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class PortfolioSummaryViewModel:
    title: str = ""
    subtitle: str = ""
    empty_state: str = ""
    fields: tuple[PortfolioSummaryFieldViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PortfolioWorkspaceViewModel:
    overview: PortfolioOverviewViewModel
    intake_status_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    template_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    project_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    scenario_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    dependency_type_options: tuple[PortfolioSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_intake_status_filter: str = "all"
    selected_scenario_id: str = ""
    selected_base_scenario_id: str = ""
    selected_compare_scenario_id: str = ""
    intake_items: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    templates: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    scenarios: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    evaluation: PortfolioSummaryViewModel = field(default_factory=PortfolioSummaryViewModel)
    comparison: PortfolioSummaryViewModel = field(default_factory=PortfolioSummaryViewModel)
    heatmap: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    dependencies: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    recent_actions: PortfolioCollectionViewModel = field(default_factory=lambda: PortfolioCollectionViewModel("", "", ""))
    active_template_summary: str = ""
    empty_state: str = ""


__all__ = [
    "PortfolioCollectionViewModel",
    "PortfolioMetricViewModel",
    "PortfolioOverviewViewModel",
    "PortfolioRecordViewModel",
    "PortfolioSelectorOptionViewModel",
    "PortfolioSummaryFieldViewModel",
    "PortfolioSummaryViewModel",
    "PortfolioWorkspaceViewModel",
]
